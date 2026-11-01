from anytext.app import App
from anytext.containers import Container
from anytext.widgets import Label


class DockAllApp(App):
    CSS_PATH = "dock_all.tcss"

    def compose(self):
        yield Container(
            Container(Label("left"), id="left"),
            Container(Label("top"), id="top"),
            Container(Label("right"), id="right"),
            Container(Label("bottom"), id="bottom"),
            id="big_container",
        )


if __name__ == "__main__":
    app = DockAllApp()
    app.run()
