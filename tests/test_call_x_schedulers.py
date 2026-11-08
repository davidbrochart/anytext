import anyio

from anytext._context import active_message_pump
from anytext.app import App
from anytext.message_pump import MessagePump


class CallLaterApp(App[None]):
    def __init__(self) -> None:
        self.display_count = 0
        super().__init__()

    def post_display_hook(self) -> None:
        self.display_count += 1


async def test_call_later() -> None:
    """Check that call later makes a call."""
    app = CallLaterApp()
    called_event = anyio.Event()

    async with app.run_test():
        app.call_later(called_event.set)
        with anyio.fail_after(1):
            await called_event.wait()


async def test_call_after_refresh() -> None:
    """Check that call later makes a call after a refresh."""
    app = CallLaterApp()

    display_count = -1

    called_event = anyio.Event()

    callback_message_pump: MessagePump | None = None

    def callback() -> None:
        nonlocal display_count
        nonlocal callback_message_pump
        called_event.set()
        display_count = app.display_count
        callback_message_pump = active_message_pump.get()

    async with app.run_test():
        app.call_after_refresh(callback)
        with anyio.fail_after(1):
            await called_event.wait()
        app_display_count = app.display_count
        assert app_display_count == display_count
        # Should be app because the callback should be in the same context as app
        assert callback_message_pump is app
