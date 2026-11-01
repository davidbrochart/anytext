from anytext.app import App
from anytext.screen import Screen
from anytext.widgets import TextArea

TEXT = """\
foo
bar
baz
"""


class AltScreen(Screen[None]):
    def compose(self):
        yield TextArea(TEXT)


class TABug(App[None]):
    def on_mount(self):
        self.push_screen(AltScreen())


if __name__ == "__main__":
    app = TABug()
    app.run()
