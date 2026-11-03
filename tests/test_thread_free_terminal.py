"""Exercise Unix terminal drivers through a real pseudo-terminal."""

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
import signal
from pathlib import Path
import anyio
from anytext import events
from anytext.app import App, ComposeResult
from anytext.widgets import Button, Input

# Queueing messages can wake async tasks and must be deferred out of the raw
# Python signal handler, which can interrupt the backend's scheduler itself.
in_resize_handler = False
original_signal = signal.signal
def register_signal(signum, handler):
    if signum == signal.SIGWINCH and callable(handler):
        callback = handler
        def handler(*args):
            global in_resize_handler
            in_resize_handler = True
            try:
                callback(*args)
            finally:
                in_resize_handler = False
    return original_signal(signum, handler)
signal.signal = register_signal

state_path = Path(os.environ["TEST_STATE"])
def forbidden(*args, **kwargs):
    raise AssertionError("Unexpected thread creation or thread offload")
thread_free = os.environ["ANYTEXT_THREADS"] == "0"
inline = os.environ["TEST_INLINE"] == "1"
if thread_free:
    anyio.to_thread.run_sync = forbidden

class TerminalApp(App):
    BINDINGS = [("escape", "quit", "Quit"), ("f2", "suspend_once", "Suspend")]
    def __init__(self):
        super().__init__()
        self.ready = False
        self.value = ""
        self.clicks = 0
        self.suspensions = 0
        self.resumes = 0
        self.last_size = None
    def compose(self) -> ComposeResult:
        yield Input()
        yield Button("Count", id="count")
    def record(self):
        data = dict(ready=self.ready, value=self.value, clicks=self.clicks,
                    suspensions=self.suspensions, resumes=self.resumes,
                    size=self.last_size)
        if self.ready:
            button = self.query_one(Button)
            data["button"] = list(button.region)
            data["active"] = button.has_class("-active")
        temporary = state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data))
        temporary.replace(state_path)
    def on_mount(self):
        if thread_free:
            assert self._runtime.portal is None
            assert self._driver.__class__.__name__ == "LinuxAsyncDriver"
            assert self._driver._writer_thread is None
            assert self._driver._key_thread is None
        else:
            expected = "LinuxInlineDriver" if inline else "LinuxDriver"
            assert self._driver.__class__.__name__ == expected
            if not inline:
                assert self._driver._writer_thread is not None
            assert self._driver._key_thread is not None
        self.app_resume_signal.subscribe(self, self.record_resume, immediate=True)
        self.ready = True
        self.set_interval(0.03, self.record)
        self.record()
    def record_resume(self, app):
        self.resumes += 1
        self.record()
    async def action_suspend_once(self):
        async with self.suspend():
            assert self._driver._key_thread._finished.is_set()
            assert self._driver._writer_thread._task.done()
            print("SUSPENDED", flush=True)
        self.suspensions += 1
        self.query_one(Input).focus()
        self.record()
    def post_message(self, message):
        if isinstance(message, events.Resize):
            assert not in_resize_handler, "Resize was queued inside a raw signal handler"
        return super().post_message(message)
    def on_resize(self, event):
        self.last_size = list(event.size)
    def on_input_changed(self, event: Input.Changed):
        self.value = event.value
        self.record()
    def on_button_pressed(self):
        self.clicks += 1
        self.record()

async def main():
    # Backends may create their own wakeup FD when starting the loop, but
    # application startup must not create socket pairs in either mode.
    socket.socketpair = forbidden
    app = TerminalApp()
    await app.run_async(inline=inline)
    if thread_free:
        assert app._driver._input_task is None
    else:
        assert app._driver._key_thread._finished.is_set()
        if not inline:
            assert app._driver._writer_thread._task.done()
    print("TERMINAL_SUCCESS", flush=True)

anyio.run(main, backend=os.environ["TEST_BACKEND"])
"""


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
@pytest.mark.parametrize("threads, inline", [("0", False), ("1", False), ("1", True)])
def test_terminal_io(tmp_path, backend, threads, inline):
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
        "ANYTEXT_THREADS": threads,
        "TEST_STATE": str(state_path),
        "TEST_BACKEND": backend,
        "TEST_INLINE": str(int(inline)),
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
                    return state
            assert process.poll() is None, transcript.decode(errors="replace")
            time.sleep(0.01)
        pytest.fail(
            f"Last state: {state_path.read_text() if state_path.exists() else None}\n"
            + transcript.decode(errors="replace")
        )

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
        if threads == "1" and not inline:
            os.write(master, b"\x1bOQ")  # F2 suspends and resumes the native driver.
            wait_for(lambda state: state["suspensions"] == 1)
            os.write(master, b"x")
            wait_for(lambda state: state["value"] == "x")
            os.kill(process.pid, signal.SIGTSTP)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                drain()
                pid, status = os.waitpid(process.pid, os.WUNTRACED | os.WNOHANG)
                if pid:
                    assert os.WIFSTOPPED(status), transcript.decode(errors="replace")
                    break
                time.sleep(0.01)
            else:
                pytest.fail("Terminal driver did not suspend the process")
            os.kill(process.pid, signal.SIGCONT)
            wait_for(lambda state: state["resumes"] == 2)
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
        assert b"TERMINAL_SUCCESS" in transcript
        assert termios.tcgetattr(slave) == original
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        os.close(master)
        os.close(slave)
