from anytext.app import App, ComposeResult
from anytext.containers import Horizontal
from anytext.widgets import Static


class NestingDemo(App):
    """App with nested CSS."""

    CSS_PATH = "nesting02.tcss"

    def compose(self) -> ComposeResult:
        with Horizontal(id="questions"):
            yield Static("Yes", classes="button affirmative")
            yield Static("No", classes="button negative")


if __name__ == "__main__":
    app = NestingDemo()
    app.run()
