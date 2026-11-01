from anytext.app import App, ComposeResult
from anytext.containers import Horizontal
from anytext.widgets import Static


class HeightApp(App[None]):

    CSS = """
    Horizontal {
        border: solid red;
        height: auto;
    }

    Static {
        border: solid green;
        width: auto;
    }

    #fill_parent {
        height: 100%;
    }

    #static {
        height: 16;
    }
    """

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Static("As tall as container", id="fill_parent"),
            Static("This has default\nheight\nbut a\nfew lines"),
            Static("I have a static height", id="static"),
        )


if __name__ == "__main__":
    HeightApp().run()
