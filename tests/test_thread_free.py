"""Exercise WASM execution paths without a browser or native thread support."""

import io
import socket
from functools import partial

import anyio
import pytest
import pytest_asyncio

from anytext import _async, constants
from anytext.app import App, ComposeResult
from anytext.drivers.callback_driver import CallbackDriver
from anytext.widgets import DirectoryTree, Input, Log, Markdown
from anytext.worker import WorkerError


@pytest_asyncio.fixture
async def no_threads(monkeypatch):
    monkeypatch.setattr(constants, "THREADS_ENABLED", False)

    def forbidden(*args, **kwargs):
        raise AssertionError("Thread-free mode attempted to use threads or sockets")

    monkeypatch.setattr(anyio.to_thread, "run_sync", forbidden)
    monkeypatch.setattr(socket, "socketpair", forbidden)


async def test_widgets_without_threads(no_threads, tmp_path):
    document = tmp_path / "hello.md"
    document.write_text("# Hello\n\nWASM document")
    (tmp_path / "child").mkdir()

    class TestApp(App):
        def compose(self) -> ComposeResult:
            yield Markdown()
            yield Log()
            yield DirectoryTree(tmp_path)

    app = TestApp()
    async with app.run_test() as pilot:
        assert app._runtime.portal is None
        await app.query_one(Markdown).load(document)
        log = app.query_one(Log)
        log.write_line("hello world")
        tree = app.query_one(DirectoryTree)
        with anyio.fail_after(5):
            while len(tree.root.children) < 2 or log.virtual_size.width < 11:
                await pilot.pause()
        assert {node.data.path.name for node in tree.root.children} == {
            "hello.md",
            "child",
        }
        with pytest.raises(WorkerError, match="Thread workers are disabled"):
            app.run_worker(lambda: None, thread=True)
        worker = app.run_worker(anyio.sleep(0))
        await worker.wait()


async def test_sync_adapter_cancellation(no_threads):
    calls = []
    with anyio.CancelScope() as scope:
        scope.cancel()
        await _async.run_sync(calls.append, "should not run")
    assert calls == []


async def test_callback_driver(no_threads):
    output = []

    class TestApp(App):
        def compose(self) -> ComposeResult:
            yield Input(id="input")

    app = TestApp(driver_class=partial(CallbackDriver, output=output.append))
    async with app.run_test(headless=False, size=(80, 24)) as pilot:
        driver = app._driver
        assert isinstance(driver, CallbackDriver)
        driver.feed_input("hello")
        await pilot.pause()
        assert app.query_one(Input).value == "hello"
        driver.feed_input("\x1b[200~ paste\x1b[201~")
        await pilot.pause()
        assert app.query_one(Input).value == "hello paste"
        driver.resize(100, 30)
        await pilot.pause()
        assert app.size.width == 100
        assert app.size.height == 30
        # Escape must be emitted after the parser timeout, even with no new input.
        app.bind("escape", "quit")
        driver.feed_input("\x1b")
        with anyio.fail_after(3):
            while not app._exit:
                await anyio.sleep(0.01)
        assert output
    assert driver._parser_task is None
    assert any("\x1b[?1049l" in data for data in output)


async def test_file_delivery(no_threads, tmp_path):
    from anytext import events

    delivered = []

    class TestApp(App):
        def on_delivery_complete(self, event: events.DeliveryComplete):
            delivered.append(event)

    async with TestApp().run_test() as pilot:
        destination = tmp_path / "result.bin"
        pilot.app._driver.deliver_binary(
            io.BytesIO(b"\x00\xff"), delivery_key="test", save_path=destination
        )
        with anyio.fail_after(3):
            while not delivered:
                await pilot.pause()
        assert destination.read_bytes() == b"\x00\xff"
        assert delivered[0].key == "test"


async def test_file_delivery_failure(no_threads, tmp_path):
    from anytext import events

    failed = []

    class TestApp(App):
        def on_delivery_failed(self, event: events.DeliveryFailed):
            failed.append(event)

    source = io.StringIO("hello")
    async with TestApp().run_test() as pilot:
        pilot.app._driver.deliver_binary(
            source, delivery_key="missing", save_path=tmp_path / "missing" / "file"
        )
        with anyio.fail_after(3):
            while not failed:
                await pilot.pause()
        assert failed[0].key == "missing"
        assert source.closed


async def test_native_driver_is_rejected(no_threads):
    class NativeDriver(CallbackDriver):
        requires_threads = True

    from anytext import _async

    async with _async.task_context():
        with pytest.raises(RuntimeError, match="driver requires threads"):
            NativeDriver(App())
