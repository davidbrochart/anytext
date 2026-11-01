from anytext.app import App, ComposeResult
from anytext.widgets import Checkbox, Footer


class ScrollOffByOne(App):
    AUTO_FOCUS = None

    def compose(self) -> ComposeResult:
        for number in range(1, 100):
            yield Checkbox(str(number))
        yield Footer()

    def on_mount(self) -> None:
        self.screen.scroll_end()


app = ScrollOffByOne()
if __name__ == "__main__":
    app.run()
