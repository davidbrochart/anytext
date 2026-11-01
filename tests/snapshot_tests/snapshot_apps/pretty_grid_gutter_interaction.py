"""App used as regression test for https://github.com/Textualize/textual/pull/4219."""

from __future__ import annotations

from anytext.app import App, ComposeResult
from anytext.containers import Grid
from anytext.widgets import Pretty, Label


class MyGrid(Grid):
    """A simple grid with 2 columns and 2 rows."""


class MyApp(App[None]):
    DEFAULT_CSS = """
    MyGrid {
        height: auto;
        grid-rows: auto;
        grid-size: 2;
        grid-gutter: 1;
        background: green;
    }

    Pretty {
        background: red;
    }

    Label {
        background: blue;
    }
"""

    def compose(self) -> ComposeResult:
        with MyGrid():
            yield Pretty(["This is a string that has some chars"])
            yield Label()
            yield Label("This should be 1 cell away from ^")


if __name__ == "__main__":
    MyApp().run()
