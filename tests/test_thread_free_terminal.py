"""Exercise the Unix driver through a real pseudo-terminal, without threads."""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform in {"win32", "emscripten", "wasi"}, reason="Requires a Unix terminal"
)

CHILD = """
import json
import os
import socket
import threading
from pathlib import Path
import anyio
from anytext.app import App, ComposeResult
from anytext.widgets import Button, Input

state_path = Path(os.environ["TEST_STATE"])
def forbidden(*args, **kwargs):
    raise AssertionError("Unexpected thread creation or thread offload")
threading.Thread.start = forbidden
anyio.to_thread.run_sync = forbidden

class TerminalApp(App):
    BINDINGS = [("escape", "quit", "Quit")]
    def __init__(self):
        super().__init__()
        self.ready = False
        self.value = ""
        self.clicks = 0
        self.last_size = None
    def compose(self) -> ComposeResult:
        yield Input()
        yield Button("Count", id="count")
    def record(self):
        data = dict(ready=self.ready, value=self.value, clicks=self.clicks,
                    size=self.last_size, threads=threading.active_count())
        if self.ready:
            button = self.query_one(Button)
            data["button"] = list(button.region)
            data["active"] = button.has_class("-active")
        temporary = state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data))
        temporary.replace(state_path)
    def on_mount(self):
        assert self._runtime.portal is None
        assert self._runtime._reader is None
        assert self._driver.__class__.__name__ == "LinuxAsyncDriver"
        assert self._driver._writer_thread is None
        assert self._driver._key_thread is None
        self.ready = True
        self.set_interval(0.03, self.record)
        self.record()
    def on_resize(self, event):
        self.last_size = list(event.size)
    def on_input_changed(self, event: Input.Changed):
        self.value = event.value
        self.record()
    def on_button_pressed(self):
        self.clicks += 1
        self.record()

async def main():
    # The Python loop is already running, so any socket pair after this point
    # would come from the application rather than the backend's own wakeup FD.
    socket.socketpair = forbidden
    app = TerminalApp()
    await app.run_async()
    assert app._driver._input_task is None
    assert threading.active_count() == 1
    print("THREAD_FREE_SUCCESS", flush=True)

anyio.run(main, backend=os.environ["TEST_BACKEND"])
"""


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_terminal_io_without_threads(tmp_path, backend):
    import fcntl
    import pty
    import struct
    import termios

    master, slave = pty.openpty()
    original = termios.tcgetattr(slave)
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
    os.set_blocking(master, False)
    state_path = tmp_path / "state.json"
    env = {
        **os.environ,
        "ANYTEXT_THREADS": "0",
        "TEST_STATE": str(state_path),
        "TEST_BACKEND": backend,
        "TERM": "xterm-256color",
    }
    process = subprocess.Popen(
        [sys.executable, "-c", CHILD],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        env=env,
        start_new_session=True,
    )
    transcript = bytearray()

    def drain():
        while True:
            try:
                data = os.read(master, 65536)
            except (BlockingIOError, OSError):
                return
            if not data:
                return
            transcript.extend(data)

    def wait_for(predicate):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            drain()
            if state_path.exists():
                state = json.loads(state_path.read_text())
                if predicate(state):
                    assert state["threads"] == 1
                    return state
            assert process.poll() is None, transcript.decode(errors="replace")
            time.sleep(0.01)
        pytest.fail(transcript.decode(errors="replace"))

    try:
        wait_for(lambda state: state["ready"] and state.get("button", [0, 0, 0])[2])
        # Split a UTF-8 character across reads.
        os.write(master, b"caf\xc3")
        time.sleep(0.02)
        os.write(master, b"\xa9")
        state = wait_for(lambda state: state["value"] == "café")
        x, y, width, height = state["button"]
        column, row = x + width // 2 + 1, y + height // 2 + 1
        os.write(master, f"\x1b[<0;{column};{row}M\x1b[<0;{column};{row}m".encode())
        wait_for(lambda state: state["clicks"] == 1 and not state["active"])
        # Resize through the same OS signal used by desktop terminals.
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 100, 0, 0))
        os.kill(process.pid, signal.SIGWINCH)
        wait_for(lambda state: state["size"] == [100, 30])
        # A lone Escape must time out and quit without a subsequent input byte.
        os.write(master, b"\x1b")
        deadline = time.monotonic() + 10
        while process.poll() is None and time.monotonic() < deadline:
            drain()
            time.sleep(0.01)
        assert process.poll() == 0, transcript.decode(errors="replace")
        drain()
        assert b"THREAD_FREE_SUCCESS" in transcript
        assert termios.tcgetattr(slave) == original
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        os.close(master)
        os.close(slave)
