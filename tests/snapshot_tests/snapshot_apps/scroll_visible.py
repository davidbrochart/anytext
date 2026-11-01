from anytext.app import App, ComposeResult
from anytext.containers import VerticalScroll
from anytext.widgets import Label, Static


# Checks  https://github.com/Textualize/textual/issues/2181
class MyCustomWidget(Static):
    def compose(self) -> ComposeResult:
        yield Label(("|\n" * 100)[:-1])
        yield Label("SHOULD BE VISIBLE", id="target")


class MyApp(App):
    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield MyCustomWidget()

    def key_t(self) -> None:
        self.query_one("#target").scroll_visible()


if __name__ == "__main__":
    MyApp().run()
