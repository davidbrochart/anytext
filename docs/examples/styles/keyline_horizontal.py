from anytext.app import App, ComposeResult
from anytext.containers import Horizontal
from anytext.widgets import Placeholder


class KeylineApp(App):
    CSS_PATH = "keyline_horizontal.tcss"

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Placeholder()
            yield Placeholder()
            yield Placeholder()


if __name__ == "__main__":
    app = KeylineApp()
    app.run()
