from anytext.app import App, ComposeResult
from anytext.widgets import Label


class BorderTitleApp(App):
    CSS_PATH = "border_title_colors.tcss"

    def compose(self) -> ComposeResult:
        yield Label("Hello, World!")

    def on_mount(self) -> None:
        label = self.query_one(Label)
        label.border_title = "Anytext Rocks"
        label.border_subtitle = "Anytext Rocks"


if __name__ == "__main__":
    app = BorderTitleApp()
    app.run()
