from anytext.app import App
from anytext.widget import Widget


class HeightApp(App):
    CSS_PATH = "height.tcss"

    def compose(self):
        yield Widget()


if __name__ == "__main__":
    app = HeightApp()
    app.run()
