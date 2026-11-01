from anytext.app import App, ComposeResult
from anytext.widgets import Header, Footer, Input


class InputWidthAutoApp(App[None]):
    CSS = """
    Input.auto {
        width: auto;
        max-width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="This has auto width", classes="auto")
        yield Footer()


if __name__ == "__main__":
    InputWidthAutoApp().run()
