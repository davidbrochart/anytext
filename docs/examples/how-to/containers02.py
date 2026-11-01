from anytext.app import App, ComposeResult
from anytext.containers import Vertical
from anytext.widgets import Placeholder


class Box(Placeholder):
    """Example widget."""

    DEFAULT_CSS = """
    Box {
        width: 16;
        height: 8;        
    }
    """


class ContainerApp(App):
    """Simple app to play with containers."""

    def compose(self) -> ComposeResult:
        with Vertical():  # (1)!
            yield Box()
            yield Box()
            yield Box()


if __name__ == "__main__":
    app = ContainerApp()
    app.run()
