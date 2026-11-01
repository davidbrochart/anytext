from __future__ import annotations

from typing import IO

import anyio

from anytext import _async


class WriterThread:
    """Buffer terminal output and offload writes through AnyIO."""

    def __init__(self, file: IO[str]) -> None:
        self._file = file
        self._pending: list[str] = []
        self._ready = _async.Event()
        self._closing = False
        self._task: _async.Task | None = None

    def start(self) -> None:
        self._task = _async.create_task(self.run(), name="anytext-output")

    def write(self, text: str) -> None:
        """Queue output from the app loop without blocking it."""
        self._pending.append(text)
        self._ready.set()

    def isatty(self) -> bool:
        return True

    def fileno(self) -> int:
        return self._file.fileno()

    def flush(self) -> None:
        """Wake the output task; stop() awaits the final flush."""
        self._ready.set()

    async def run(self) -> None:
        limiter = anyio.CapacityLimiter(1)

        def write(text: str) -> None:
            self._file.write(text)
            self._file.flush()

        while True:
            await self._ready.wait()
            self._ready.clear()
            if self._pending:
                text = "".join(self._pending)
                self._pending.clear()
                await anyio.to_thread.run_sync(write, text, limiter=limiter)
            if self._closing and not self._pending:
                return

    async def stop(self) -> None:
        """Drain buffered output and await the last write."""
        self._closing = True
        self._ready.set()
        if self._task is not None:
            with anyio.CancelScope(shield=True):
                await self._task
