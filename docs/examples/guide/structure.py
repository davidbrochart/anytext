from datetime import datetime

from anytext.app import App
from anytext.widget import Widget


class Clock(Widget):
    """A clock app."""

    DEFAULT_CSS = """
    Clock {
        content-align: center middle;
    }
    """

    def on_mount(self):
        self.set_interval(1, self.refresh)

    def render(self):
        return datetime.now().strftime("%c")


class ClockApp(App):
    def compose(self):
        yield Clock()


if __name__ == "__main__":
    app = ClockApp()
    app.run()
