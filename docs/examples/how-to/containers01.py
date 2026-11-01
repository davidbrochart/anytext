from anytext.app import App, ComposeResult
from anytext.containers import Horizontal
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
        with Horizontal():  # (1)!
            yield Box()  # (2)!
            yield Box()
            yield Box()


if __name__ == "__main__":
    app = ContainerApp()
    app.run()
