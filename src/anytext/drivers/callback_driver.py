"""A terminal driver for hosts which supply input and consume ANSI output."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Callable

import anyio

from anytext import _async, events
from anytext._xterm_parser import XTermParser
from anytext.driver import Driver
from anytext.geometry import Size

if TYPE_CHECKING:
    from anytext.app import App


class CallbackDriver(Driver):
    """Run a terminal on the app loop, without threads or native terminal APIs.

    Call ``feed_input`` with terminal input strings, and ``resize`` when the
    host terminal changes size. These methods must run on the app's event loop.
    ``output`` receives ANSI terminal output synchronously and must not block.
    """

    def __init__(
        self,
        app: App,
        *,
        debug: bool = False,
        mouse: bool = True,
        size: tuple[int, int] | None = None,
        output: Callable[[str], object] | None = None,
    ) -> None:
        super().__init__(app, debug=debug, mouse=mouse, size=size)
        self._output = output if output is not None else sys.__stdout__.write
        self._parser = XTermParser(debug=debug)
        self._active = False
        self._parser_task: _async.Task | None = None

    def write(self, data: str) -> None:
        self._output(data)

    def feed_input(self, data: str) -> None:
        """Receive decoded terminal input from the host on the app loop."""
        if self._active and data:
            for event in self._parser.feed(data):
                self.process_message(event)

    def resize(self, width: int, height: int) -> None:
        """Receive terminal dimensions (in cells) from the host."""
        if width < 1 or height < 1:
            raise ValueError("Terminal dimensions must be positive")
        self._size = (width, height)
        if self._active:
            size = Size(width, height)
            self.send_message(events.Resize(size, size))

    async def _tick(self) -> None:
        while True:
            await anyio.sleep(0.01)
            for event in self._parser.tick():
                self.process_message(event)

    def start_application_mode(self) -> None:
        if self._active:
            return
        self._parser = XTermParser(debug=self._debug)
        self._active = True
        self.write("\x1b[?1049h\x1b[?25l\x1b[?7l\x1b[?2004h\x1b[?1004h")
        if self._mouse:
            self.write("\x1b[?1000h\x1b[?1003h\x1b[?1006h")
        self.resize(*(self._size or (80, 24)))
        self._parser_task = _async.create_task(self._tick(), name="terminal-input")

    def disable_input(self) -> None:
        self._active = False
        if self._parser_task is not None:
            self._parser_task.cancel()
            self._parser_task = None

    def stop_application_mode(self) -> None:
        self.disable_input()
        if self._mouse:
            self.write("\x1b[?1000l\x1b[?1003l\x1b[?1006l")
        self.write("\x1b[?2004l\x1b[?1004l\x1b[?7h\x1b[?25h\x1b[?1049l")

    def close(self) -> None:
        self.disable_input()
