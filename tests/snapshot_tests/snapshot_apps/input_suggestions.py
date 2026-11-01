from anytext.app import App, ComposeResult
from anytext.suggester import SuggestFromList
from anytext.widgets import Input


fruits = ["apple", "pear", "mango", "peach", "strawberry", "blueberry", "banana"]


class FruitsApp(App[None]):
    CSS = """
    Input > .input--suggestion {
        color: red;
        text-style: italic;
    }
    """

    def compose(self) -> ComposeResult:
        yield Input("straw", suggester=SuggestFromList(fruits), select_on_focus=False)
        yield Input("straw", suggester=SuggestFromList(fruits))
        yield Input("p", suggester=SuggestFromList(fruits))
        yield Input("b", suggester=SuggestFromList(fruits))
        yield Input("a", suggester=SuggestFromList(fruits))


if __name__ == "__main__":
    app = FruitsApp()
    app.run()
