import pytest
from rich.style import Style

from anytext.color import Color
from anytext.css.errors import StyleValueError
from anytext.css.styles import Styles


def test_box_normalization():
    """Check that none or hidden is normalized to empty string."""
    styles = Styles()
    styles.border_left = ("none", "red")
    assert styles.border_left == ("", Color.parse("red"))


@pytest.mark.parametrize("style_attr", ["text_style", "link_style"])
def test_text_style_none_with_others(style_attr):
    """Style "none" mixed with others should give custom Anytext exception."""
    styles = Styles()

    with pytest.raises(StyleValueError):
        setattr(styles, style_attr, "bold none underline italic")


@pytest.mark.parametrize("style_attr", ["text_style", "link_style"])
def test_text_style_set_to_none(style_attr):
    """Setting text style to "none" should clear the styles."""
    styles = Styles()
    setattr(styles, style_attr, "bold underline italic")
    assert getattr(styles, style_attr) != Style.null()
    setattr(styles, style_attr, "none")
    assert getattr(styles, style_attr) == Style.null()
