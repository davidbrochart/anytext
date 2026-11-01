from anytext.app import App, ComposeResult
from anytext.widgets import Welcome

class WelcomeApp(App[None]):

    def compose(self) -> ComposeResult:
        yield Welcome()

if __name__ == "__main__":
    WelcomeApp().run()
