from anytext.app import App, ComposeResult
from anytext.containers import Grid
from anytext.widgets import Placeholder


class KeylineApp(App):
    CSS_PATH = "keyline.tcss"

    def compose(self) -> ComposeResult:
        with Grid():
            yield Placeholder(id="foo")
            yield Placeholder(id="bar")
            yield Placeholder()
            yield Placeholder(classes="hidden")
            yield Placeholder(id="baz")


if __name__ == "__main__":
    KeylineApp().run()
