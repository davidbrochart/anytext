from anytext.app import App
from anytext.widgets import Header, Label, Footer


class TestApp(App):
    BINDINGS = [("ctrl+q", "app.quit", "Quit")]
    CSS = """
    
    Label {
        border: solid red;
    }
    Footer {
        height: 4;
    }
    """

    def compose(self):
        text = (
            "this is a sample sentence and here are some words".replace(" ", "\n") * 2
        )
        yield Header()
        yield Label(text)
        yield Footer()


if __name__ == "__main__":
    app = TestApp()
    app.run()
