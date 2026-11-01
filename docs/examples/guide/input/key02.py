from anytext import events
from anytext.app import App, ComposeResult
from anytext.widgets import RichLog


class InputApp(App):
    """App to display key events."""

    def compose(self) -> ComposeResult:
        yield RichLog()

    def on_key(self, event: events.Key) -> None:
        self.query_one(RichLog).write(event)

    def key_space(self) -> None:
        self.bell()


if __name__ == "__main__":
    app = InputApp()
    app.run()
