"""AnyIO-owned blocking terminal workers."""

from __future__ import annotations

from typing import Callable

import anyio

from anytext import _async


class ThreadWorker:
    """Run a cancellable terminal loop in an AnyIO worker.

    The blocking callback must call ``anyio.from_thread.check_cancelled()``
    between reads. Completion is awaited on the app loop, never synchronously.
    A separate limiter keeps long-lived input loops out of the default budget.
    """

    def __init__(self, target: Callable[[], None], *, name: str) -> None:
        self._target = target
        self._name = name
        self._started = False
        self._finished = _async.Event()
        self._task: _async.Task | None = None

    @property
    def started(self) -> bool:
        return self._started

    def start(self) -> None:
        if self._task is not None:
            raise RuntimeError("Worker has already been started")
        self._task = _async.create_task(self._run(), name=self._name)

    async def _run(self) -> None:
        def invoke() -> None:
            anyio.from_thread.check_cancelled()
            self._started = True
            self._target()

        try:
            await anyio.to_thread.run_sync(invoke, limiter=anyio.CapacityLimiter(1))
        finally:
            self._finished.set()

    async def wait(self) -> None:
        if self._task is not None:
            with anyio.CancelScope(shield=True):
                try:
                    await self._task
                except anyio.get_cancelled_exc_class():
                    pass

    async def stop(self) -> None:
        """Request cooperative cancellation and await resource cleanup."""
        if self._task is not None:
            self._task.cancel()
            await self.wait()
