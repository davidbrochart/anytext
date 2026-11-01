import os
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
        self._closed = False

    def close(self) -> None:
        """Close the reader (will exit the iterator)."""
        self._closed = True

    def __iter__(self) -> Iterator[bytes]:
        """Read input, yield bytes."""
        while not self._closed:
            anyio.from_thread.check_cancelled()
            try:
                data = os.read(self._fileno, 1024) or None
            except Exception:
                break
            if not data:
                break
            yield data
