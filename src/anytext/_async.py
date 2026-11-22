"""Backend independent task ownership and completion primitives for Anytext.

Every background task belongs to the running app's AnyIO task group. The small
handles here retain the optionally-awaitable operations used by the public API.
"""

from __future__ import annotations

from contextlib import AsyncExitStack, asynccontextmanager
from contextvars import ContextVar, copy_context
from functools import wraps
from typing import Any, Awaitable, Callable, Generic, TypeVar, cast

import anyio
import anyio.to_thread
import sniffio
from anyio.abc import TaskGroup
from anyio.from_thread import BlockingPortal

from anytext import constants

T = TypeVar("T")
_runtime: ContextVar[Runtime] = ContextVar("anytext_runtime")
_task: ContextVar[Task | None] = ContextVar("anytext_task", default=None)
sleep = anyio.sleep


class ResettableEvent:
    """An AnyIO event that can be cleared for subsequent waiters."""

    def __init__(self) -> None:
        self._event = anyio.Event()

    def set(self) -> None:
        self._event.set()

    def clear(self) -> None:
        if self._event.is_set():
            self._event = anyio.Event()

    async def wait(self) -> None:
        await self._event.wait()


class Task(Generic[T]):
    """An app task that preserves the original exception for its awaiters."""

    def __init__(
        self,
        group: TaskGroup,
        awaitable: Awaitable[T],
        name: str | None,
        on_done: Callable[[], None] | None,
    ) -> None:
        self._native_id: int | None = None
        self._error: BaseException | None = None
        self._handle = group.start_soon(self._run, awaitable, on_done, name=name)

    def done(self) -> bool:
        return self._handle.status not in (
            anyio.TaskHandle.Status.PENDING,
            anyio.TaskHandle.Status.CANCELLING,
        )

    def exception(self) -> BaseException | None:
        if not self.done():
            raise RuntimeError("Result is not ready")
        return self._error

    async def wait(self) -> None:
        """Wait for completion without retrieving the task's outcome."""
        await self._handle.wait()

    async def _wait(self) -> T:
        await self.wait()
        if self._error is not None:
            raise self._error
        return cast(T, self._handle.return_value)

    def __await__(self):
        return self._wait().__await__()

    def cancel(self) -> None:
        self._handle.cancel()

    async def _run(
        self, awaitable: Awaitable[T], on_done: Callable[[], None] | None
    ) -> T | None:
        self._native_id = anyio.get_current_task().id
        token = _task.set(self)
        try:
            return await awaitable
        except BaseException as error:
            self._error = error
            # Ordinary errors and cancellation are delivered to awaiters.
            # Fatal exceptions still reach the app's task group.
            if not isinstance(error, (Exception, anyio.get_cancelled_exc_class())):
                raise
            return None
        finally:
            try:
                if on_done is not None:
                    on_done()
            finally:
                _task.reset(token)


def current_task() -> Task | None:
    task = _task.get()
    return (
        task
        if task is not None and task._native_id == anyio.get_current_task().id
        else None
    )


def create_task(
    awaitable: Awaitable[T],
    *,
    name: str | None = None,
    on_done: Callable[[], None] | None = None,
) -> Task[T]:
    try:
        runtime = _runtime.get()
    except LookupError:
        if hasattr(awaitable, "close"):
            awaitable.close()
        raise RuntimeError("Background tasks require a running Anytext app") from None
    return Task(runtime.group, awaitable, name, on_done)


async def gather(*awaitables: Awaitable) -> list[Any]:
    results: list[Any] = [None] * len(awaitables)
    errors: list[BaseException] = []

    async def collect(index: int, awaitable: Awaitable) -> None:
        try:
            results[index] = await awaitable
        except BaseException as error:
            if isinstance(error, anyio.get_cancelled_exc_class()):
                raise
            errors.append(error)

    async with anyio.create_task_group() as group:
        for index, awaitable in enumerate(awaitables):
            group.start_soon(collect, index, awaitable)
    if errors:
        raise errors[0]
    return results


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

    def __init__(self, group, portal, exit_stack: AsyncExitStack) -> None:
        self.group = group
        self.portal = portal
        self.exit_stack = exit_stack
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

        if self._in_foreign_trio_loop():
            return self._call_from_foreign_trio_loop(invoke, asynchronous=False)
        return anyio.from_thread.run_sync(invoke, token=self.token)

    def _in_foreign_trio_loop(self) -> bool:
        """Identify a Trio loop running inside an async thread worker."""
        if self.backend != "trio":
            return False
        try:
            return (
                sniffio.current_async_library() == "trio"
                and anyio.lowlevel.current_token() != self.token
            )
        except RuntimeError:
            return False

    # TODO: Remove this workaround and both _in_foreign_trio_loop() branches
    # once the fix in https://github.com/agronholm/anyio/pull/1469 is released
    # and Anytext's minimum AnyIO version includes it.
    def _call_from_foreign_trio_loop(self, callback, *, asynchronous):
        """Bridge a different Trio loop without creating another worker thread.

        Trio's from_thread helpers reject every running Trio loop, including a
        loop in a different thread. Its public token submission API accepts
        this case, so use it to deliver work to the owning task group.
        """
        from concurrent.futures import Future as BlockingFuture

        result = BlockingFuture()
        context = copy_context()

        async def run():
            try:
                result.set_result(await callback())
            except BaseException as error:
                result.set_exception(error)

        def dispatch():
            try:
                if asynchronous:
                    self.group.start_soon(run)
                else:
                    result.set_result(callback())
            except BaseException as error:
                result.set_exception(error)

        self.token.native_token.run_sync_soon(context.run, dispatch)
        return result.result()

    def call_from_thread(self, callback):
        if self.portal is None:
            raise RuntimeError("Thread workers are disabled in thread-free mode")

        async def invoke():
            token = _runtime.set(self)
            try:
                return await callback()
            finally:
                _runtime.reset(token)

        if self._in_foreign_trio_loop():
            return self._call_from_foreign_trio_loop(invoke, asynchronous=True)
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
            runtime = Runtime(group, portal, stack)
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
