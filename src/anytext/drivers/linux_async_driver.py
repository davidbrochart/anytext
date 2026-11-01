"""Thread-free input and output for Unix desktop terminals."""

from __future__ import annotations

import os
from codecs import getincrementaldecoder

import anyio

from anytext import _async
from anytext._xterm_parser import XTermParser
from anytext.drivers.linux_driver import LinuxDriver


class LinuxAsyncDriver(LinuxDriver):
    """Use the app's AnyIO loop to read a Linux or macOS terminal.

    Terminal setup and event processing are shared with the native driver.
    Output is written synchronously; a slow output device may pause the app.
    """

    requires_threads = False
    _input_task: _async.Task | None = None

    def _start_writer(self) -> None:
        # No output thread: write() and flush() use the terminal directly.
        pass

    def write(self, data: str) -> None:
        self._file.write(data)

    def flush(self) -> None:
        self._file.flush()

    def _start_input(self) -> None:
        self._input_task = _async.create_task(self._read_input(), name="terminal-input")

    def _stop_input(self) -> None:
        task = self._input_task
        if task is not None:
            task.cancel()
            self._input_task = None

    async def _read_input(self) -> None:
        parser = XTermParser(self._debug)
        decode = getincrementaldecoder("utf-8")().decode
        try:
            while True:
                # Check parser timeouts even when no more input arrives (Escape
                # is ambiguous until its timeout expires).
                with anyio.move_on_after(0.05) as waiting:
                    await anyio.wait_readable(self.fileno)
                if not waiting.cancel_called:
                    data = os.read(self.fileno, 4096)
                    if not data:
                        self._app.exit()
                        return
                    text = decode(data)
                    if text:
                        for event in parser.feed(text):
                            self.process_message(event)
                for event in parser.tick():
                    self.process_message(event)
        except Exception:
            from rich.traceback import Traceback

            self._app.call_later(self._app.panic, Traceback())

    def close(self) -> None:
        self._stop_input()
        self.flush()
