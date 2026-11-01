import io
import socket
from functools import partial
from pathlib import Path

import anyio

from anytext import constants
from anytext.app import App, ComposeResult
from anytext.drivers.callback_driver import CallbackDriver
from anytext.widgets import DirectoryTree, Input, Log, Markdown

assert not constants.THREADS_ENABLED
assert constants.get_environ("ANYTEXT_THREADS") is None


def forbidden(*args, **kwargs):
    raise AssertionError("unexpected thread or socket operation")


anyio.to_thread.run_sync = forbidden
socket.socketpair = forbidden

Path("/tmp/wasm-smoke").mkdir(exist_ok=True)
Path("/tmp/wasm-smoke/hello.md").write_text("# Hello WASM")
output = []


class SmokeApp(App):
    def compose(self) -> ComposeResult:
        yield Input()
        yield Markdown()
        yield Log()
        yield DirectoryTree("/tmp/wasm-smoke")


async def main():
    app = SmokeApp(driver_class=partial(CallbackDriver, output=output.append))
    async with app.run_test(headless=False) as pilot:
        assert app._runtime.portal is None
        app.query_one(Input).focus()
        app._driver.feed_input("WASM works")
        await app.query_one(Markdown).load(Path("/tmp/wasm-smoke/hello.md"))
        app.query_one(Log).write_line("hello WASM")
        with anyio.fail_after(10):
            while (
                app.query_one(Input).value != "WASM works"
                or not app.query_one(DirectoryTree).root.children
                or app.query_one(Log).virtual_size.width < 10
            ):
                await pilot.pause()
        app._driver.resize(100, 30)
        await pilot.pause()
        assert app.size.width == 100
        assert app.size.height == 30
        assert output
        app._driver.deliver_binary(
            io.BytesIO(b"wasm file"),
            delivery_key="test",
            save_path=Path("/tmp/wasm.bin"),
        )
        with anyio.fail_after(3):
            while not Path("/tmp/wasm.bin").exists():
                await pilot.pause()
        assert Path("/tmp/wasm.bin").read_bytes() == b"wasm file"
        app.bind("escape", "quit")
        app._driver.feed_input("\x1b")
        with anyio.fail_after(3):
            while not app._exit:
                await anyio.sleep(0.01)
    assert any("\x1b[?1049l" in data for data in output)
