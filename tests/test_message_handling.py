from anytext.app import App, ComposeResult
from anytext.message import Message
from anytext.widget import Widget


async def test_message_inheritance_namespace():
    """Inherited messages get their correct namespaces.

    Regression test for https://github.com/Textualize/textual/issues/1814.
    """

    class BaseWidget(Widget):
        class Fired(Message):
            pass

        def trigger(self) -> None:
            self.post_message(self.Fired())

    class Left(BaseWidget):
        class Fired(BaseWidget.Fired):
            pass

    class Right(BaseWidget):
        class Fired(BaseWidget.Fired):
            pass

    class DummyWidget(Widget):
        # ensure that referencing a message type in other class scopes
        # doesn't break the namespace
        _event = Left.Fired

    handlers_called = []
    received = anyio.Event()

    def record(name):
        handlers_called.append(name)
        if len(handlers_called) == 2:
            received.set()

    class MessageInheritanceApp(App[None]):
        def compose(self) -> ComposeResult:
            yield Left()
            yield Right()

        def on_left_fired(self):
            record("left")

        def on_right_fired(self):
            record("right")

    app = MessageInheritanceApp()
    async with app.run_test():
        app.query_one(Left).trigger()
        app.query_one(Right).trigger()
        with anyio.fail_after(5):
            await received.wait()

    assert sorted(handlers_called) == ["left", "right"]


import anyio
