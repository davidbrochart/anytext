from __future__ import annotations

from collections import deque
from queue import Empty as QueueEmpty
from typing import Generic, TypeVar

from textual._async import Event

QueueType = TypeVar("QueueType")


class Queue(Generic[QueueType]):
    """An unbounded queue built on AnyIO events.

    This has just enough functionality to run the message pumps.

    """

    def __init__(self) -> None:
        self.values: deque[QueueType] = deque()
        self.ready_event = Event()
        self._unfinished = 0
        self._finished = Event()
        self._finished.set()

    def put_nowait(self, value: QueueType) -> None:
        self.values.append(value)
        self._unfinished += 1
        self._finished.clear()
        self.ready_event.set()

    def qsize(self) -> int:
        return len(self.values)

    def empty(self) -> bool:
        return not self.values

    async def put(self, value: QueueType) -> None:
        self.put_nowait(value)

    def task_done(self) -> None:
        if self._unfinished <= 0:
            raise ValueError("task_done() called too many times")
        self._unfinished -= 1
        if not self._unfinished:
            self._finished.set()

    async def join(self) -> None:
        await self._finished.wait()

    async def get(self) -> QueueType:
        while not self.values:
            await self.ready_event.wait()
        value = self.values.popleft()
        if not self.values:
            self.ready_event.clear()
        return value

    def get_nowait(self) -> QueueType:
        if not self.values:
            raise QueueEmpty()
        value = self.values.popleft()
        if not self.values:
            self.ready_event.clear()
        return value
