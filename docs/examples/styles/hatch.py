from anytext.app import App, ComposeResult
from anytext.containers import Horizontal, Vertical
from anytext.widgets import Static

HATCHES = ("cross", "horizontal", "custom", "left", "right")


class HatchApp(App):
    CSS_PATH = "hatch.tcss"

    def compose(self) -> ComposeResult:
        with Horizontal():
            for hatch in HATCHES:
                static = Static(classes=f"hatch {hatch}")
                static.border_title = hatch
                with Vertical():
                    yield static


if __name__ == "__main__":
    app = HatchApp()
    app.run()
