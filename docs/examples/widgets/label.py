from anytext.app import App, ComposeResult
from anytext.widgets import Label


class LabelApp(App):
    def compose(self) -> ComposeResult:
        yield Label("Hello, world!")


if __name__ == "__main__":
    app = LabelApp()
    app.run()
