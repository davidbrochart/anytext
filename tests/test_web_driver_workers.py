"""Exercise the server driver with real pipes and AnyIO worker threads."""

import os
import subprocess
import sys

import pytest

CHILD = """
import os
import anyio
from anytext.app import App
from anytext.drivers.web_driver import WebDriver

class RemoteApp(App):
    seen = False
    def on_key(self, event):
        if event.key == "q":
            self.seen = True
            self.exit()

async def main():
    app = RemoteApp(driver_class=WebDriver)
    await app.run_async()
    assert app.seen
    assert app._driver._key_thread._finished.is_set()
    print("REMOTE_SUCCESS")

anyio.run(main, backend=os.environ["TEST_BACKEND"])
"""


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_server_input_and_shutdown(backend):
    process = subprocess.Popen(
        [sys.executable, "-c", CHILD],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "ANYTEXT_THREADS": "1", "TEST_BACKEND": backend},
    )
    try:
        # A framed key press, followed by EOF, as sent by the external server.
        stdout, stderr = process.communicate(b"D\x00\x00\x00\x01q", timeout=15)
        assert process.returncode == 0, stderr.decode(errors="replace")
        assert stdout.startswith(b"__GANGLION__\n")
        assert b"REMOTE_SUCCESS" in stdout
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
