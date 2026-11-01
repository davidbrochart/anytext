from anytext.app import App
from anytext.containers import Grid
from anytext.widgets import Label


class MyApp(App):
    CSS_PATH = "grid_columns.tcss"

    def compose(self):
        yield Grid(
            Label("1fr"),
            Label("width = 16"),
            Label("2fr"),
            Label("1fr"),
            Label("width = 16"),
            Label("1fr"),
            Label("width = 16"),
            Label("2fr"),
            Label("1fr"),
            Label("width = 16"),
        )


if __name__ == "__main__":
    app = MyApp()
    app.run()
