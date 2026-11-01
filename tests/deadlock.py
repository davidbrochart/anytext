"""
Called by test_pipe.py

"""

from anytext.app import App
from anytext.binding import Binding
from anytext.widgets import Footer


class MyApp(App[None]):
    BINDINGS = [
        Binding(key="q", action="quit", description="Quit the app"),
    ]

    def compose(self):
        yield Footer()


app = MyApp()
app.run()
