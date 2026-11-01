from anytext.app import App, ComposeResult
from anytext.screen import Screen
from anytext.binding import Binding
from anytext.widgets import Footer


class ShowBindingScreen(Screen):
    BINDINGS = [
        Binding("p", "app.pop_screen", "Binding shown"),
    ]

    def compose(self) -> ComposeResult:
        yield Footer()


class HideBindingApp(App):
    """Regression test for https://github.com/Textualize/textual/issues/4382"""

    BINDINGS = [
        Binding("p", "app.pop_screen", "Binding hidden", show=False),
    ]

    def on_mount(self) -> None:
        self.push_screen(ShowBindingScreen())


if __name__ == "__main__":
    app = HideBindingApp()
    app.run()
