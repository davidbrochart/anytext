"""Run the bundled demo in Pyodide with browser-provided terminal callbacks."""

import os

# xterm.js supports RGB colors; do not rely on native-terminal detection in WASM.
os.environ["ANYTEXT_COLOR_SYSTEM"] = "truecolor"

from anytext import constants
from anytext.demo.demo_app import DemoApp
from anytext.drivers.callback_driver import CallbackDriver

assert not constants.THREADS_ENABLED

browser_driver = None


class BrowserDriver(CallbackDriver):
    """Adapt host operations without changing the demo's screens or widgets."""

    def open_url(self, url, new_tab=True):
        terminal_open_url(url)

    def deliver_binary(
        self, binary, *, delivery_key, save_path, mime_type=None, name=None, **options
    ):
        try:
            terminal_download(
                save_path.name, binary.read(), mime_type or "application/octet-stream"
            )
            self._delivery_complete(delivery_key, save_path=None, name=name)
        except Exception as error:
            self._delivery_failed(delivery_key, exception=error, name=name)
        finally:
            binary.close()


def make_driver(app, **options):
    global browser_driver
    browser_driver = BrowserDriver(app, output=terminal_write, **options)
    return browser_driver


def browser_input(data):
    if browser_driver is not None:
        browser_driver.feed_input(data)


def browser_resize(width, height):
    if browser_driver is not None:
        browser_driver.resize(width, height)


class BrowserDemo(DemoApp):
    def on_mount(self):
        browser_ready()


browser_app = BrowserDemo(driver_class=make_driver)
