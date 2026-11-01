"""
App to test alignment containers.
"""

from anytext.app import App, ComposeResult
from anytext.containers import Center, Middle
from anytext.widgets import Button


class AlignContainersApp(App[None]):
    CSS = """
    Center {
        tint: $primary 10%;
    }
    Middle {
        tint: $accent 10%;
    }
    """

    def compose(self) -> ComposeResult:
        with Center():
            yield Button.success("center")
        with Middle():
            yield Button.error("middle")


app = AlignContainersApp()
if __name__ == "__main__":
    app.run()
