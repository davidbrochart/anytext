from anytext.app import App, ComposeResult
from anytext.widgets import Digits


class DigitApp(App):
    CSS = """
    Screen {
        align: center middle;
    }
    #pi {
        border: double green;
        width: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Digits("3.141,592,653,5897", id="pi")


if __name__ == "__main__":
    app = DigitApp()
    app.run()
