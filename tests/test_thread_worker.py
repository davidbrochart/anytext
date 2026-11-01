"""Async completion, cancellation and pool isolation for terminal workers."""

from io import StringIO

import anyio
import pytest

from anytext import _async
from anytext._thread_worker import ThreadWorker
from anytext.drivers._writer_thread import WriterThread


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_worker_lifecycle(backend):
    async def check():
        async with _async.task_context():
            entered = anyio.Event()
            stop = anyio.Event()
            cleaned_up = []

            def work():
                try:
                    anyio.from_thread.run_sync(entered.set)
                    anyio.from_thread.run(stop.wait)
                finally:
                    cleaned_up.append(True)

            worker = ThreadWorker(work, name="test-input")
            worker.start()
            with anyio.fail_after(5):
                await entered.wait()
                assert worker.started
                # This must leave the loop free to finish the from_thread call.
                stop.set()
                await worker.stop()
            assert cleaned_up == [True]
            await worker.stop()

    anyio.run(check, backend=backend)


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_stop_before_worker_starts(backend):
    async def check():
        called = []
        async with _async.task_context():
            worker = ThreadWorker(lambda: called.append(True), name="never-started")
            worker.start()
            await worker.stop()
        assert not called

    anyio.run(check, backend=backend)


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_writer_startup_and_drain(backend):
    async def check():
        output = StringIO()
        async with _async.task_context():
            writer = WriterThread(output)
            writer.start()
            for _ in range(100):
                writer.write("startup\n")
            await anyio.sleep(0)
            for _ in range(100):
                writer.write("running\n")
            await writer.stop()
        assert output.getvalue() == "startup\n" * 100 + "running\n" * 100

    anyio.run(check, backend=backend)


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_writer_stop_without_yielding(backend):
    async def check():
        output = StringIO()
        async with _async.task_context():
            writer = WriterThread(output)
            writer.start()
            writer.write("restored terminal")
            await writer.stop()
        assert output.getvalue() == "restored terminal"

    anyio.run(check, backend=backend)


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_terminal_workers_do_not_exhaust_default_pool(backend):
    async def check():
        limiter = anyio.to_thread.current_default_thread_limiter()
        limiter.total_tokens = 1
        workers = []
        stops = []
        async with _async.task_context():
            try:
                for _ in range(3):
                    entered = anyio.Event()
                    stop = anyio.Event()
                    stops.append(stop)

                    def run(entered=entered, stop=stop):
                        anyio.from_thread.run_sync(entered.set)
                        anyio.from_thread.run(stop.wait)

                    worker = ThreadWorker(run, name="long-lived-terminal")
                    workers.append(worker)
                    worker.start()
                    with anyio.fail_after(5):
                        await entered.wait()
                assert await anyio.to_thread.run_sync(lambda: 42) == 42
            finally:
                for stop in stops:
                    stop.set()
                for worker in workers:
                    await worker.stop()

    anyio.run(check, backend=backend)


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_stop_after_submission_before_callback(backend, monkeypatch):
    async def check():
        submitted = anyio.Event()
        release = anyio.Event()
        original = anyio.to_thread.run_sync
        called = []

        async def delayed(callback, **kwargs):
            submitted.set()
            await release.wait()
            return await original(callback, **kwargs)

        monkeypatch.setattr(anyio.to_thread, "run_sync", delayed)
        async with _async.task_context():
            worker = ThreadWorker(lambda: called.append(True), name="delayed-input")
            worker.start()
            await submitted.wait()
            await worker.stop()
            release.set()
        assert not called

    anyio.run(check, backend=backend)
