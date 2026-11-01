from anytext.app import App, ComposeResult
from anytext.widgets import Header, Footer


class ExampleApp(App):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()


if __name__ == "__main__":
    app = ExampleApp()
    app.run()
