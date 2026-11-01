"""
This module contains constants, which may be set in environment variables.
"""

from __future__ import annotations

import os
import sys
from typing import get_args

from typing_extensions import Final, TypeGuard

from anytext._types import AnimationLevel

get_environ = os.environ.get


def _get_environ_bool(name: str) -> bool:
    """Check an environment variable switch.

    Args:
        name: Name of environment variable.

    Returns:
        `True` if the env var is "1", otherwise `False`.
    """
    has_environ = get_environ(name) == "1"
    return has_environ


def _get_environ_int(
    name: str, default: int, minimum: int | None = None, maximum: int | None = None
) -> int:
    """Retrieves an integer environment variable.

    Args:
        name: Name of environment variable.
        default: The value to use if the value is not set, or set to something other
            than a valid integer.
        minimum: Optional minimum value.

    Returns:
        The integer associated with the environment variable if it's set to a valid int
            or the default value otherwise.
    """
    try:
        value = int(os.environ[name])
    except KeyError:
        return default
    except ValueError:
        return default
    if minimum is not None:
        return max(minimum, value)
    if maximum is not None:
        return min(maximum, value)
    return value


def _get_environ_port(name: str, default: int) -> int:
    """Get a port no. from an environment variable.

    Note that there is no 'minimum' here, as ports are more like names than a scalar value.

    Args:
        name: Name of environment variable.
        default: The value to use if the value is not set, or set to something other
            than a valid port.

    Returns:
        An integer port number.

    """
    try:
        value = int(os.environ[name])
    except KeyError:
        return default
    except ValueError:
        return default
    if value < 0 or value > 65535:
        return default
    return value


def _is_valid_animation_level(value: str) -> TypeGuard[AnimationLevel]:
    """Checks if a string is a valid animation level.

    Args:
        value: The string to check.

    Returns:
        Whether it's a valid level or not.
    """
    return value in get_args(AnimationLevel)


def _get_anytext_animations() -> AnimationLevel:
    """Get the value of the environment variable that controls anytext animations.

    The variable can be in any of the values defined by [`AnimationLevel`][anytext.constants.AnimationLevel].

    Returns:
        The value that the variable was set to. If the environment variable is set to an
            invalid value, we default to showing all animations.
    """
    value: str = get_environ("ANYTEXT_ANIMATIONS", "FULL").lower()
    if _is_valid_animation_level(value):
        return value
    return "full"


# WASM builds generally cannot create Python threads. Keep the decision explicit
# so desktop applications can exercise exactly the same execution path.
THREADS_ENABLED: Final[bool] = get_environ(
    "ANYTEXT_THREADS", "1"
) != "0" and sys.platform not in {"emscripten", "wasi"}
"""Allow thread workers and native terminal drivers. Disabled with ANYTEXT_THREADS=0."""


DEBUG: Final[bool] = _get_environ_bool("ANYTEXT_DEBUG")
"""Enable debug mode."""

DRIVER: Final[str | None] = get_environ("ANYTEXT_DRIVER", None)
"""Import for replacement driver."""

DISABLE_KITTY_KEY: Final[bool] = _get_environ_bool("ANYTEXT_DISABLE_KITTY_KEY")
"""Disable kitty key protocol."""

FILTERS: Final[str] = get_environ("ANYTEXT_FILTERS", "")
"""A list of filters to apply to renderables."""

LOG_FILE: Final[str | None] = get_environ("ANYTEXT_LOG", None)
"""A last resort log file that appends all logs, when devtools isn't working."""

DEVTOOLS_HOST: Final[str] = get_environ("ANYTEXT_DEVTOOLS_HOST", "127.0.0.1")
"""The host where textual console is running."""

DEVTOOLS_PORT: Final[int] = _get_environ_port("ANYTEXT_DEVTOOLS_PORT", 8081)
"""Constant with the port that the devtools will connect to."""

SCREENSHOT_DELAY: Final[int] = _get_environ_int("ANYTEXT_SCREENSHOT", -1, minimum=-1)
"""Seconds delay before taking screenshot, -1 for no screenshot."""

SCREENSHOT_LOCATION: Final[str | None] = get_environ("ANYTEXT_SCREENSHOT_LOCATION")
"""The location where screenshots should be written."""

SCREENSHOT_FILENAME: Final[str | None] = get_environ("ANYTEXT_SCREENSHOT_FILENAME")
"""The filename to use for the screenshot."""

PRESS: Final[str] = get_environ("ANYTEXT_PRESS", "")
"""Keys to automatically press."""

SHOW_RETURN: Final[bool] = _get_environ_bool("ANYTEXT_SHOW_RETURN")
"""Write the return value on exit."""

MAX_FPS: Final[int] = _get_environ_int("ANYTEXT_FPS", 60, minimum=1)
"""Maximum frames per second for updates."""

COLOR_SYSTEM: Final[str | None] = get_environ("ANYTEXT_COLOR_SYSTEM", "auto")
"""Force color system override."""

ANYTEXT_ANIMATIONS: Final[AnimationLevel] = _get_anytext_animations()
"""Determines whether animations run or not."""

ESCAPE_DELAY: Final[float] = _get_environ_int("ESCDELAY", 100, minimum=1) / 1000.0
"""The delay (in seconds) before reporting an escape key (not used if the extend key protocol is available)."""

SLOW_THRESHOLD: int = _get_environ_int("ANYTEXT_SLOW_THRESHOLD", 500, minimum=100)
"""The time threshold (in milliseconds) after which a warning is logged 
if message processing exceeds this duration.
"""

DEFAULT_THEME: Final[str] = get_environ("ANYTEXT_THEME", "anytext-dark")
"""Anytext theme to make default. More than one theme may be specified in a comma separated list.
Anytext will use the first theme that exists.
"""

SMOOTH_SCROLL: Final[bool] = _get_environ_int("ANYTEXT_SMOOTH_SCROLL", 1) == 1
"""Should smooth scrolling be enabled? set `ANYTEXT_SMOOTH_SCROLL=0` to disable smooth scrolling.
"""

DIM_FACTOR: Final[float] = (
    _get_environ_int("ANYTEXT_DIM_FACTOR", 66, minimum=0, maximum=100) / 100
)
"""Percentage to use as opacity when converting ANSI 'dim' attribute to RGB."""
