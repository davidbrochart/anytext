from anytext.app import App, ComposeResult
from anytext.containers import Vertical
from anytext.widgets import Static


class AutoApp(App):
    """The innermost container should push its parents outwards, to fill the screen."""

    CSS = """
    #outer {
        background: blue;
        height: auto;
        border: solid white;
    } 

    #inner {
        background: green;
        height: auto;
        border: solid yellow;
    }

    #innermost {
        background: cyan;
        height: 1fr;
        color: auto;        
    }
            
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="outer"):
            with Vertical(id="inner"):
                with Vertical(id="innermost"):
                    yield Static("Hello\nWorld!\nfoo", id="helloworld")


if __name__ == "__main__":
    app = AutoApp()
    app.run()
