from anytext.app import App, ComposeResult
from anytext.containers import Grid
from anytext.widgets import Placeholder


class KeylineApp(App):
    CSS = """
    Grid {
        grid-size: 3 3;
        grid-gutter: 1;
        grid-columns: 2;
        grid-rows: 1;
        keyline: thin;
        width: auto;
        height: auto;
        background: blue;
    }
    """

    def compose(self) -> ComposeResult:
        with Grid():
            yield Placeholder("a")
            yield Placeholder("b")
            yield Placeholder("c")
            yield Placeholder("d")
            yield Placeholder("e")
            yield Placeholder("f")
            yield Placeholder("g")
            yield Placeholder("h")
            yield Placeholder("i")


if __name__ == "__main__":
    KeylineApp().run()
