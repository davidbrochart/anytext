"""AnyIO callback handoff without an application-owned socket dispatcher."""

import socket
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar

import anyio
import pytest

from anytext import _async
from anytext.app import App
from anytext.message import Message


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
@pytest.mark.parametrize("worker_backend", ["asyncio", "trio"])
def test_bridge_from_async_thread_worker(backend, worker_backend):
    """An async worker may own a different loop in its native worker thread."""
    marker = ContextVar("bridge_marker", default=None)

    class Ping(Message):
        pass

    async def check():
        app = App()
        async with app.run_test():
            runtime = app._runtime

            def sync_callback():
                assert runtime.in_event_loop()
                assert _async.get_runtime() is runtime
                assert marker.get() == "worker"
                return 42

            async def async_callback():
                await anyio.sleep(0)
                return sync_callback()

            def fail():
                raise ValueError("callback failed")

            async def worker():
                marker.set("worker")
                assert not runtime.in_event_loop()
                assert runtime.run_sync_from_thread(sync_callback) == 42
                assert app.call_from_thread(async_callback) == 42
                with pytest.raises(ValueError, match="callback failed"):
                    runtime.run_sync_from_thread(fail)
                with pytest.raises(ValueError, match="callback failed"):
                    app.call_from_thread(fail)
                assert app.post_message(Ping())

            with anyio.fail_after(10):
                await anyio.to_thread.run_sync(
                    lambda: anyio.run(worker, backend=worker_backend)
                )

    anyio.run(check, backend=backend)


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_callback_bridge_without_socketpair(backend, monkeypatch):
    async def check():
        def forbidden(*args, **kwargs):
            raise AssertionError("Application created a socket pair")

        monkeypatch.setattr(socket, "socketpair", forbidden)
        async with _async.task_context() as runtime:

            async def background():
                return 42

            def callback():
                assert runtime.in_event_loop()
                assert _async.get_runtime() is runtime
                return _async.create_task(background())

            task = await anyio.to_thread.run_sync(
                runtime.run_sync_from_thread, callback
            )
            assert await task == 42
            calls = []

            def fail():
                calls.append(True)
                raise ValueError("callback failed")

            with pytest.raises(ValueError, match="callback failed"):
                await anyio.to_thread.run_sync(runtime.run_sync_from_thread, fail)
            assert calls == [True]

    anyio.run(check, backend=backend)


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_callback_from_external_executor(backend):
    async def check():
        async with _async.task_context() as runtime:

            def callback():
                assert runtime.in_event_loop()
                assert _async.get_runtime() is runtime
                return 42

            def external():
                # Simulate a third-party executor with no AnyIO worker token or
                # copied app context. The explicit loop token selects the app.
                def submit():
                    with pytest.raises(LookupError):
                        _async.get_runtime()
                    result = runtime.run_sync_from_thread(callback)
                    with pytest.raises(LookupError):
                        _async.get_runtime()
                    return result

                with ThreadPoolExecutor(max_workers=1) as executor:
                    return executor.submit(submit).result(timeout=5)

            with anyio.fail_after(5):
                assert await anyio.to_thread.run_sync(external) == 42

    anyio.run(check, backend=backend)


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_post_message_is_queued_before_returning(backend):
    class Ping(Message):
        pass

    async def check():
        app = App()
        async with app.run_test():
            message = Ping()
            original_put = app._message_queue.put_nowait
            inserted = []
            received = anyio.Event()

            def put(item):
                original_put(item)
                if item is message:
                    inserted.append(item)
                    received.set()

            app._message_queue.put_nowait = put

            def post():
                assert app.post_message(message)
                assert inserted == [message]

            with anyio.fail_after(5):
                await anyio.to_thread.run_sync(post)
                await received.wait()

    anyio.run(check, backend=backend)
