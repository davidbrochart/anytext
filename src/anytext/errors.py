"""
General exception classes.

"""

from __future__ import annotations


class AnytextError(Exception):
    """Base class for Anytext errors."""


class NoWidget(AnytextError):
    """Specified widget was not found."""


class RenderError(AnytextError):
    """An object could not be rendered."""


class DuplicateKeyHandlers(AnytextError):
    """More than one handler for a single key press.

    For example, if the handlers `key_ctrl_i` and `key_tab` were defined on the same
    widget, then this error would be raised.
    """
