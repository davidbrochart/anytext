from anytext.app import App, ComposeResult
from anytext.widgets import Footer, Header


class StopwatchApp(App):
    """A Anytext app to manage stopwatches."""

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "anytext-dark" if self.theme == "anytext-light" else "anytext-light"
        )


if __name__ == "__main__":
    app = StopwatchApp()
    app.run()
