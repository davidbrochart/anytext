"""Check the public configuration and names exposed by Anytext."""

import os
import subprocess
import sys

from anytext.app import App
from anytext.logging import AnytextHandler


def test_environment_settings():
    environment = {
        **os.environ,
        "ANYTEXT": "debug",
        "ANYTEXT_THEME": "anytext-light",
        "ANYTEXT_ANIMATIONS": "none",
        "ANYTEXT_FPS": "30",
        "ANYTEXT_SMOOTH_SCROLL": "0",
    }
    subprocess.run(
        [
            sys.executable,
            "-c",
            "from anytext import constants; from anytext.app import App; "
            "assert constants.DEFAULT_THEME == 'anytext-light'; "
            "assert constants.ANYTEXT_ANIMATIONS == 'none'; "
            "assert constants.MAX_FPS == 30; "
            "assert not constants.SMOOTH_SCROLL; "
            "assert App().debug",
        ],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


async def test_builtin_theme_switching():
    app = App()
    async with app.run_test():
        app.theme = "anytext-light"
        assert not app.current_theme.dark
        app.action_toggle_dark()
        assert app.theme == "anytext-dark"
        assert app.current_theme.dark
        app.action_toggle_dark()
        assert app.theme == "anytext-light"


def test_logging_handler():
    handler = AnytextHandler()
    assert handler.__class__.__module__ == "anytext.logging"
