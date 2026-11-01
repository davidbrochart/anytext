from anytext.app import App
from anytext.containers import Horizontal
from anytext.widgets import Placeholder


class MinHeightApp(App):
    CSS_PATH = "min_height.tcss"

    def compose(self):
        yield Horizontal(
            Placeholder("min-height: 25%", id="p1"),
            Placeholder("min-height: 75%", id="p2"),
            Placeholder("min-height: 30", id="p3"),
            Placeholder("min-height: 40w", id="p4"),
        )


if __name__ == "__main__":
    app = MinHeightApp()
    app.run()
