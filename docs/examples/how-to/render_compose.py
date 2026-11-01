from time import time

from anytext.app import App, ComposeResult, RenderResult
from anytext.containers import Container
from anytext.renderables.gradient import LinearGradient
from anytext.widgets import Static

COLORS = [
    "#881177",
    "#aa3355",
    "#cc6666",
    "#ee9944",
    "#eedd00",
    "#99dd55",
    "#44dd88",
    "#22ccbb",
    "#00bbcc",
    "#0099cc",
    "#3366bb",
    "#663399",
]
STOPS = [(i / (len(COLORS) - 1), color) for i, color in enumerate(COLORS)]


class Splash(Container):
    """Custom widget that extends Container."""

    DEFAULT_CSS = """
    Splash {
        align: center middle;
    }
    Static {
        width: 40;
        padding: 2 4;
    }
    """

    def on_mount(self) -> None:
        self.auto_refresh = 1 / 30  # (1)!

    def compose(self) -> ComposeResult:
        yield Static("Making a splash with Anytext!")  # (2)!

    def render(self) -> RenderResult:
        return LinearGradient(time() * 90, STOPS)  # (3)!


class SplashApp(App):
    """Simple app to show our custom widget."""

    def compose(self) -> ComposeResult:
        yield Splash()


if __name__ == "__main__":
    app = SplashApp()
    app.run()
