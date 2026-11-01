"""
Simulates a screenshot of the Anytext devtools
"""

from textual_dev.renderables import DevConsoleHeader

from anytext.app import App
from anytext.widgets import Static


class ConsoleApp(App):
    def compose(self):
        yield Static(DevConsoleHeader())


app = ConsoleApp()
