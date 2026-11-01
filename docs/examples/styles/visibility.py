from anytext.app import App
from anytext.widgets import Label


class VisibilityApp(App):
    CSS_PATH = "visibility.tcss"

    def compose(self):
        yield Label("Widget 1")
        yield Label("Widget 2", classes="invisible")
        yield Label("Widget 3")


if __name__ == "__main__":
    app = VisibilityApp()
    app.run()
