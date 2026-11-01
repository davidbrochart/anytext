from anytext.app import App, ComposeResult
from anytext.widgets import Input


class InputApp(App):
    def compose(self) -> ComposeResult:
        yield Input(placeholder="First Name")
        yield Input(placeholder="Last Name")


if __name__ == "__main__":
    app = InputApp()
    app.run()
