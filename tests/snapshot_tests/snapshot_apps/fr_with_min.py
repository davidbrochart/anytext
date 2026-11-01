from anytext.app import App, ComposeResult
from anytext.containers import Horizontal, Vertical, VerticalScroll
from anytext.widgets import Header, Footer, Static


class ScreenSplitApp(App[None]):
    CSS = """
    Horizontal {
        width: 1fr;        
    }

    Vertical {
        width: 1fr;
        background: blue;
        min-width: 20;
    }

    #scroll1 {
        width: 1fr;
        background: $panel;
    }

    #scroll2 {
        width: 2fr;
        background: $panel;
    }

    #scroll1 Static, #scroll2 Static {
        width: 1fr;
        content-align: center middle;
        background: $boost;
    }

    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield Vertical()
            with VerticalScroll(id="scroll1"):
                for n in range(100):
                    yield Static(f"This is content number {n}")
            with VerticalScroll(id="scroll2"):
                for n in range(100):
                    yield Static(f"This is content number {n}")
        yield Footer()


if __name__ == "__main__":
    ScreenSplitApp().run()
