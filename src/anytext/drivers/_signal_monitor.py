"""Deliver Unix signals to callbacks on the app's async loop."""

from __future__ import annotations

from signal import Signals
from typing import Callable

import anyio

from anytext import _async


class SignalMonitor:
    """Register immediately and handle signals from an app-owned task."""

    def __init__(self, signum: Signals, callback: Callable[[], None]) -> None:
        self._receiver = anyio.open_signal_receiver(signum)
        signals = self._receiver.__enter__()

        async def receive() -> None:
            async for _ in signals:
                callback()

        self._task = _async.create_task(receive(), name="terminal-signals")

    async def stop(self) -> None:
        """Join the receiver task and release its signal handler."""
        with anyio.CancelScope(shield=True):
            self._task.cancel()
            try:
                await self._task
            except anyio.get_cancelled_exc_class():
                pass
            finally:
                self._receiver.__exit__(None, None, None)
