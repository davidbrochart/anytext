from anytext.app import App, ComposeResult
from anytext.binding import Binding
from anytext.widgets import Footer

class MApp(App):
    BINDINGS = [Binding("o,ctrl+o", "options", "Options")]
    def compose(self) -> ComposeResult:
        yield Footer()

if __name__ == "__main__":
    MApp().run()
