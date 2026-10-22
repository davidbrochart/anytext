from __future__ import annotations

from anyio import Lock, get_current_task


class RLock:
    """A re-entrant AnyIO lock."""

    def __init__(self) -> None:
        self._owner: int | None = None
        self._count = 0
        self._lock = Lock()

    async def acquire(self) -> None:
        """Wait until the lock can be acquired."""
        task = get_current_task().id
        assert task is not None
        if self._owner is None or self._owner != task:
            await self._lock.acquire()
            self._owner = task
        self._count += 1

    def release(self) -> None:
        """Release a previously acquired lock."""
        task = get_current_task().id
        assert task is not None
        if self._owner != task or not self._count:
            raise RuntimeError("RLock can only be released by its owner")
        self._count -= 1
        if not self._count:
            self._owner = None
            self._lock.release()

    @property
    def is_locked(self):
        """Return True if lock is acquired."""
        return self._lock.locked()

    async def __aenter__(self) -> None:
        """Asynchronous context manager to acquire and release lock."""
        await self.acquire()

    async def __aexit__(self, _type, _value, _traceback) -> None:
        """Exit the context manager."""
        self.release()
