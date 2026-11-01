from anytext.app import App
from anytext.widget import Widget


class WidthApp(App):
    CSS_PATH = "width.tcss"

    def compose(self):
        yield Widget()


if __name__ == "__main__":
    app = WidthApp()
    app.run()
