from anytext.app import App, ComposeResult
from anytext.containers import Horizontal
from anytext.widgets import OptionList


class MissingScrollbarApp(App[None]):
    CSS = """
    OptionList {
        height: 1fr;
    }

    #left {
        min-width: 25;
    }

    #middle {
        width: 5fr;
    }

    #right {
        min-width: 30;
    }
    """

    def compose(self) -> ComposeResult:
        options = [str(n) for n in range(200)]
        with Horizontal():
            yield OptionList(*options, id="left")
            yield OptionList(*options, id="middle")
            yield OptionList(*options, id="right")


if __name__ == "__main__":
    MissingScrollbarApp().run()
