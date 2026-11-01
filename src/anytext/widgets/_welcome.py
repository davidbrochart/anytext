"""Provides a Anytext welcome widget."""

from rich.markdown import Markdown

from anytext.app import ComposeResult
from anytext.containers import Container
from anytext.widgets._button import Button
from anytext.widgets._static import Static

WELCOME_MD = """\
# Welcome!

Anytext is a TUI, or *Text User Interface*, framework for Python inspired by modern web development. **We hope you enjoy using Anytext!**

## Dune quote

> "I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."
"""


class Welcome(Static):
    """A Anytext welcome widget.

    This widget can be used as a form of placeholder within a Anytext
    application; although also see
    [Placeholder][anytext.widgets._placeholder.Placeholder].
    """

    DEFAULT_CSS = """
        Welcome {
            width: 100%;
            height: 100%;
            background: $surface;
        }

        Welcome Container {
            padding: 1;
            color: $foreground;
        }

        Welcome #text {
            margin:  0 1;
        }

        Welcome #close {
            dock: bottom;
            width: 100%;
        }
    """

    def compose(self) -> ComposeResult:
        yield Container(Static(Markdown(WELCOME_MD), id="text"), id="md")
        yield Button("OK", id="close", variant="success")
