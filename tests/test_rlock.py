import anyio
import pytest

from anytext.rlock import RLock


async def test_simple_lock():
    lock = RLock()
    # Starts not locked
    assert not lock.is_locked
    # Acquire the lock
    await lock.acquire()
    assert lock.is_locked
    # Acquire a second time (should not block)
    await lock.acquire()
    assert lock.is_locked

    # Release the lock
    lock.release()
    # Should still be locked
    assert lock.is_locked
    # Release the lock
    lock.release()
    # Should be released
    assert not lock.is_locked

    # Another release is a runtime error
    with pytest.raises(RuntimeError):
        lock.release()


async def test_multiple_tasks() -> None:
    """Check RLock prevents other tasks from acquiring lock."""
    lock = RLock()

    started: list[int] = []
    done: list[int] = []
    task_started = {n: anyio.Event() for n in (1, 2)}

    async def test_task(n: int) -> None:
        started.append(n)
        task_started[n].set()
        async with lock:
            done.append(n)

    async with anyio.create_task_group() as group:
        async with lock:
            assert done == []
            group.start_soon(test_task, 1)
            group.start_soon(test_task, 2)
            with anyio.fail_after(1):
                await task_started[1].wait()
                await task_started[2].wait()
            assert sorted(started) == [1, 2]
            assert done == []

    assert sorted(done) == [1, 2]
