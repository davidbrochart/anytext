from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Callable

import anyio

from anytext._thread_worker import ThreadWorker
from anytext.driver import Driver
from anytext.drivers import win32
from anytext.drivers._writer_thread import WriterThread

if TYPE_CHECKING:
    from anytext.app import App


class WindowsDriver(Driver):
    """Powers display and input for Windows."""

    requires_threads = True

    def __init__(
        self,
        app: App,
        *,
        debug: bool = False,
        mouse: bool = True,
        size: tuple[int, int] | None = None,
    ) -> None:
        """Initialize Windows driver.

        Args:
            app: The App instance.
            debug: Enable debug mode.
            mouse: Enable mouse support.
            size: Initial size of the terminal or `None` to detect.
        """
        super().__init__(app, debug=debug, mouse=mouse, size=size)
        self._file = sys.__stdout__
        self._event_thread: ThreadWorker | None = None
        self._restore_console: Callable[[], None] | None = None
        self._writer_thread: WriterThread | None = None

    @property
    def can_suspend(self) -> bool:
        """Can this driver be suspended?"""
        return True

    def write(self, data: str) -> None:
        """Write data to the output device.

        Args:
            data: Raw data.
        """
        assert self._writer_thread is not None, "Driver must be in application mode"
        self._writer_thread.write(data)

    def _enable_mouse_support(self) -> None:
        """Enable reporting of mouse events."""
        if not self._mouse:
            return
        write = self.write
        write("\x1b[?1000h")  # SET_VT200_MOUSE
        write("\x1b[?1003h")  # SET_ANY_EVENT_MOUSE
        write("\x1b[?1015h")  # SET_VT200_HIGHLIGHT_MOUSE
        write("\x1b[?1006h")  # SET_SGR_EXT_MODE_MOUSE
        self.flush()

    def _disable_mouse_support(self) -> None:
        """Disable reporting of mouse events."""
        if not self._mouse:
            return
        write = self.write
        write("\x1b[?1000l")
        write("\x1b[?1003l")
        write("\x1b[?1015l")
        write("\x1b[?1006l")
        self.flush()

    def _enable_bracketed_paste(self) -> None:
        """Enable bracketed paste mode."""
        self.write("\x1b[?2004h")

    def _disable_bracketed_paste(self) -> None:
        """Disable bracketed paste mode."""
        self.write("\x1b[?2004l")

    def start_application_mode(self) -> None:
        """Start application mode."""

        self._restore_console = win32.enable_application_mode()

        self._writer_thread = WriterThread(self._file)
        self._writer_thread.start()

        self.write("\x1b[?1049h")  # Enable alt screen
        self._enable_mouse_support()
        self.write("\x1b[?25l")  # Hide cursor
        self.write("\033[?1004h")  # Enable FocusIn/FocusOut.
        self.write("\x1b[>1u")  # https://sw.kovidgoyal.net/kitty/keyboard-protocol/
        self.flush()
        self._enable_bracketed_paste()

        monitor = win32.EventMonitor(self._app, self.process_message)
        self._event_thread = ThreadWorker(monitor.run, name="anytext-input")
        self._event_thread.start()

    async def disable_input(self) -> None:
        self._disable_mouse_support()
        if self._event_thread is not None:
            await self._event_thread.stop()
            self._event_thread = None

    async def stop_application_mode(self) -> None:
        """Stop application mode, restore state."""
        self._disable_bracketed_paste()
        await self.disable_input()

        # Disable the Kitty keyboard protocol. This must be done before leaving
        # the alt screen. https://sw.kovidgoyal.net/kitty/keyboard-protocol/
        self.write("\x1b[<u")

        # Disable alt screen, show cursor
        self.write("\x1b[?1049l" + "\x1b[?25h")
        self.write("\033[?1004l")  # Disable FocusIn/FocusOut.
        self.flush()

    async def close(self) -> None:
        """Perform cleanup."""
        if self._writer_thread is not None:
            await self._writer_thread.stop()
        if self._restore_console:
            self._restore_console()
