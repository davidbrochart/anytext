import anyio
import pytest

from anytext.app import App, ComposeResult
from anytext.widgets import RichLog


def test_call_from_thread_app_not_running():
    app = App()

    # Should fail if app is not running
    with pytest.raises(RuntimeError):
        app.call_from_thread(print)


def test_call_from_thread():
    """Test the call_from_thread method."""

    def update_app(app):
        def write_stuff(text: str) -> None:
            app.query_one(RichLog).write(text)

        app.call_from_thread(write_stuff, "Hello")
        app.call_from_thread(app.exit, 123)

    class ThreadTestApp(App[object]):
        """Trivial app with a single widget."""

        def compose(self) -> ComposeResult:
            yield RichLog()

        async def on_ready(self) -> None:
            """Launch a thread which will modify the app."""
            try:
                self.call_from_thread(print)
            except RuntimeError as error:
                # Calling this from the same thread as the app is an error
                self._runtime_error = error
            self.run_worker(anyio.to_thread.run_sync(update_app, self))

    app = ThreadTestApp()
    result = app.run(headless=True, size=(80, 24))
    assert isinstance(app._runtime_error, RuntimeError)
    assert result == 123
