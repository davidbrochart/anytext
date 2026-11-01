import os
import selectors
import sys
from typing import Iterator

import anyio


class InputReader:
    """Read input from stdin."""

    def __init__(self, timeout: float = 0.1) -> None:
        """

        Args:
            timeout: Seconds to block for input.
        """
        self._fileno = sys.__stdin__.fileno()
        self.timeout = timeout
        self._selector = selectors.DefaultSelector()
        self._selector.register(self._fileno, selectors.EVENT_READ)
        self._closed = False

    def close(self) -> None:
        """Close the reader (will exit the iterator)."""
        self._closed = True

    def __iter__(self) -> Iterator[bytes]:
        """Read input, yield bytes."""
        fileno = self._fileno
        read = os.read
        EVENT_READ = selectors.EVENT_READ
        while not self._closed:
            anyio.from_thread.check_cancelled()
            for _key, events in self._selector.select(self.timeout):
                if events & EVENT_READ:
                    data = read(fileno, 1024)
                    if not data:
                        return
                    yield data
            yield b""
