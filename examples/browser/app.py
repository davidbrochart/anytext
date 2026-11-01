"""Loaded by browser.js into Pyodide; host callbacks are injected as globals."""

import os

# xterm.js supports RGB colors; do not rely on native-terminal detection in WASM.
os.environ["ANYTEXT_COLOR_SYSTEM"] = "truecolor"

from anytext import constants
from anytext.app import App, ComposeResult
from anytext.containers import Horizontal
from anytext.drivers.callback_driver import CallbackDriver
from anytext.widgets import Button, Footer, Header, Input, Label, Log, Markdown

assert not constants.THREADS_ENABLED

browser_driver = None


def make_driver(app, **options):
    global browser_driver
    browser_driver = CallbackDriver(app, output=terminal_write, **options)
    return browser_driver


def browser_input(data):
    if browser_driver is not None:
        browser_driver.feed_input(data)


def browser_resize(width, height):
    if browser_driver is not None:
        browser_driver.resize(width, height)


class BrowserApp(App):
    TITLE = "Anytext · Pyodide"
    CSS = """
    Screen { padding: 1 2; }
    #intro { height: auto; margin-bottom: 1; }
    Input { margin-bottom: 1; }
    #buttons { height: 3; margin-bottom: 1; }
    #counter { width: 1fr; padding: 1 2; }
    Log { border: round $primary; height: 1fr; }
    """
    BINDINGS = [("ctrl+q", "quit", "Quit")]

    def __init__(self):
        super().__init__(driver_class=make_driver)
        self.count = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield Markdown(
            "## It works in your browser\n"
            "Type a message and press **Enter**, or use the buttons. "
            "Python input, rendering, and widget updates share one event loop.",
            id="intro",
        )
        yield Input(placeholder="Type a message, then press Enter", id="message")
        with Horizontal(id="buttons"):
            yield Button("Count", id="count", variant="primary")
            yield Label("Count: 0", id="counter")
            yield Button("Quit", id="quit")
        yield Log(id="events")
        yield Footer()

    def on_mount(self):
        self.query_one(Log).write_line("Ready. No Python threads or socket bridge.")
        browser_ready()

    def on_input_submitted(self, event: Input.Submitted):
        self.query_one(Log).write_line(f"You typed: {event.value}")
        event.input.value = ""

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "quit":
            self.exit()
        else:
            self.count += 1
            self.query_one("#counter", Label).update(f"Count: {self.count}")
            self.query_one(Log).write_line(f"Count button pressed: {self.count}")


browser_app = BrowserApp()
