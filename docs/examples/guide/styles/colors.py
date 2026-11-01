from anytext.app import App, ComposeResult
from anytext.widgets import Static


class WidgetApp(App):
    def compose(self) -> ComposeResult:
        self.widget = Static("Anytext")
        yield self.widget

    def on_mount(self) -> None:
        self.widget.styles.background = "darkblue"
        self.widget.styles.border = ("heavy", "white")


if __name__ == "__main__":
    app = WidgetApp()
    app.run()
