"""Backend independent task ownership and completion primitives for Anytext.

Every background task belongs to the running app's AnyIO task group. The small
handles here retain the optionally-awaitable operations used by the public API.
"""

from __future__ import annotations

from contextlib import AsyncExitStack, asynccontextmanager
from contextvars import ContextVar
from functools import wraps
from typing import Any, Awaitable, Callable, Generic, TypeVar

import anyio
import sniffio
from anyio.from_thread import BlockingPortal

from anytext import constants

T = TypeVar("T")
_runtime: ContextVar[Runtime] = ContextVar("anytext_runtime")
_task: ContextVar[Task | None] = ContextVar("anytext_task", default=None)
sleep = anyio.sleep


class Event:
    """An AnyIO event that may be reset, with lazy backend selection."""

    def __init__(self) -> None:
        self._event: anyio.Event | None = None
        self._set = False

    def set(self) -> None:
        self._set = True
        if self._event is not None:
            self._event.set()

    def clear(self) -> None:
        if self._set:
            self._event = None
            self._set = False

    def is_set(self) -> bool:
        return self._set

    async def wait(self) -> bool:
        if self._event is None:
            self._event = anyio.Event()
            if self._set:
                self._event.set()
        await self._event.wait()
        return True


class Future(Generic[T]):
    """A reusable awaitable result, independent of the selected backend."""

    def __init__(self) -> None:
        self._event = Event()
        self._result: Any = None
        self._error: BaseException | None = None
        self._callbacks: list[Callable] = []

    def done(self) -> bool:
        return self._event.is_set()

    def set_result(self, value: T) -> None:
        if self.done():
            raise RuntimeError("Result is already set")
        self._result = value
        self._finish()

    def set_exception(self, error: BaseException) -> None:
        if self.done():
            raise RuntimeError("Result is already set")
        self._error = error
        self._finish()

    def _finish(self) -> None:
        self._event.set()
        for callback in self._callbacks:
            callback(self)
        self._callbacks.clear()

    def add_done_callback(self, callback: Callable) -> None:
        if self.done():
            callback(self)
        else:
            self._callbacks.append(callback)

    def exception(self) -> BaseException | None:
        if not self.done():
            raise RuntimeError("Result is not ready")
        return self._error

    def result(self) -> T:
        if not self.done():
            raise RuntimeError("Result is not ready")
        if self._error is not None:
            raise self._error
        return self._result

    async def _wait(self) -> T:
        await self._event.wait()
        return self.result()

    def __await__(self):
        return self._wait().__await__()


class Task(Future[T]):
    """A cancellable task owned by an app's task group."""

    def __init__(self, awaitable: Awaitable[T], name: str | None = None) -> None:
        super().__init__()
        self._awaitable = awaitable
        self._scope: anyio.CancelScope | None = None
        self._cancel_requested = False
        self.name = name
        self._native_id: int | None = None

    def cancel(self) -> None:
        self._cancel_requested = True
        if self._scope is not None:
            self._scope.cancel()

    async def _run(self) -> None:
        self._native_id = anyio.get_current_task().id
        token = _task.set(self)
        try:
            with anyio.CancelScope() as scope:
                self._scope = scope
                if self._cancel_requested:
                    scope.cancel()
                try:
                    self._result = await self._awaitable
                except BaseException as error:
                    self._error = error
                    if not isinstance(
                        error, (Exception, anyio.get_cancelled_exc_class())
                    ):
                        raise
        finally:
            self._finish()
            _task.reset(token)


def current_task() -> Task | None:
    task = _task.get()
    return (
        task
        if task is not None and task._native_id == anyio.get_current_task().id
        else None
    )


def create_task(awaitable: Awaitable[T], *, name: str | None = None) -> Task[T]:
    try:
        runtime = _runtime.get()
    except LookupError:
        if hasattr(awaitable, "close"):
            awaitable.close()
        raise RuntimeError("Background tasks require a running Anytext app") from None
    task = Task(awaitable, name)
    runtime.group.start_soon(task._run, name=name)
    return task


async def gather(*awaitables: Awaitable, return_exceptions: bool = False) -> list[Any]:
    results: list[Any] = [None] * len(awaitables)
    errors: list[BaseException] = []

    async def collect(index: int, awaitable: Awaitable) -> None:
        try:
            results[index] = await awaitable
        except BaseException as error:
            if isinstance(error, anyio.get_cancelled_exc_class()):
                raise
            if return_exceptions:
                results[index] = error
            else:
                errors.append(error)

    async with anyio.create_task_group() as group:
        for index, awaitable in enumerate(awaitables):
            group.start_soon(collect, index, awaitable)
    if errors:
        raise errors[0]
    return results


ALL_COMPLETED = "ALL_COMPLETED"
FIRST_COMPLETED = "FIRST_COMPLETED"


async def wait(tasks, *, timeout=None, return_when=ALL_COMPLETED):
    tasks = set(tasks)
    done = set()
    event = anyio.Event()

    async def watch(task):
        try:
            await task
        except BaseException as error:
            if isinstance(error, anyio.get_cancelled_exc_class()) and not task.done():
                raise
        done.add(task)
        if return_when == FIRST_COMPLETED or len(done) == len(tasks):
            event.set()

    with anyio.move_on_after(timeout):
        async with anyio.create_task_group() as group:
            for task in tasks:
                group.start_soon(watch, task)
            if tasks:
                await event.wait()
            group.cancel_scope.cancel()
    return done, tasks - done


async def wait_for(awaitable, timeout):
    with anyio.fail_after(timeout):
        return await awaitable


async def shield(awaitable):
    with anyio.CancelScope(shield=True):
        return await awaitable


async def run_sync(callback: Callable[..., T], *args: Any) -> T:
    """Run built-in synchronous work, without requiring threads on WASM.

    Thread-free work runs on the app loop and must be bounded. Checkpoints allow
    cancellation and other tasks to run before and after the operation.
    """
    if constants.THREADS_ENABLED:
        return await anyio.to_thread.run_sync(callback, *args)
    await anyio.lowlevel.checkpoint()
    result = callback(*args)
    await anyio.lowlevel.checkpoint()
    return result


class Runtime:
    """Own app tasks and bridge native workers to the app loop through AnyIO."""

    def __init__(self, group, portal) -> None:
        self.group = group
        self.portal = portal
        self.token = anyio.lowlevel.current_token()
        self.backend = sniffio.current_async_library()

    def in_event_loop(self) -> bool:
        """Recognize the app loop even in signal handlers with an empty context."""
        token = sniffio.current_async_library_cvar.set(self.backend)
        try:
            return anyio.lowlevel.current_token() == self.token
        except RuntimeError:
            return False
        finally:
            sniffio.current_async_library_cvar.reset(token)

    def run_sync_from_thread(self, callback, *args):
        """Run a sync callback on this app's loop and wait for its result."""
        if self.portal is None:
            raise RuntimeError(
                "Cross-thread callbacks are disabled in thread-free mode"
            )

        def invoke():
            token = _runtime.set(self)
            try:
                return callback(*args)
            finally:
                _runtime.reset(token)

        return anyio.from_thread.run_sync(invoke, token=self.token)

    def call_from_thread(self, callback):
        if self.portal is None:
            raise RuntimeError("Thread workers are disabled in thread-free mode")

        async def invoke():
            token = _runtime.set(self)
            try:
                return await callback()
            finally:
                _runtime.reset(token)

        return self.portal.call(invoke)


@asynccontextmanager
async def task_context():
    error: BaseException | None = None
    async with anyio.create_task_group() as group:
        async with AsyncExitStack() as stack:
            portal = (
                await stack.enter_async_context(BlockingPortal())
                if constants.THREADS_ENABLED
                else None
            )
            runtime = Runtime(group, portal)
            token = _runtime.set(runtime)
            try:
                yield runtime
            except BaseException as caught:
                # Keep application exceptions intact rather than wrapping them
                # in task-group exception groups at the public app boundary.
                error = caught
            finally:
                group.cancel_scope.cancel()
                _runtime.reset(token)
    if error is not None:
        raise error


def get_runtime() -> Runtime:
    return _runtime.get()


def with_task_context(function):
    @wraps(function)
    async def wrapped(*args, **kwargs):
        async with task_context():
            return await function(*args, **kwargs)

    return wrapped
