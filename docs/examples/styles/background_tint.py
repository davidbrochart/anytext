from anytext.app import App, ComposeResult
from anytext.containers import Vertical
from anytext.widgets import Label


class BackgroundTintApp(App):
    CSS_PATH = "background_tint.tcss"

    def compose(self) -> ComposeResult:
        with Vertical(id="tint1"):
            yield Label("0%")
        with Vertical(id="tint2"):
            yield Label("25%")
        with Vertical(id="tint3"):
            yield Label("50%")
        with Vertical(id="tint4"):
            yield Label("75%")
        with Vertical(id="tint5"):
            yield Label("100%")


if __name__ == "__main__":
    app = BackgroundTintApp()
    app.run()
