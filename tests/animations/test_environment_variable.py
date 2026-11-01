import pytest

from anytext import constants
from anytext.app import App
from anytext.constants import _get_anytext_animations


@pytest.mark.parametrize(
    ["env_variable", "value"],
    [
        ("", "full"),  # default
        ("FULL", "full"),
        ("BASIC", "basic"),
        ("NONE", "none"),
        ("garbanzo beans", "full"),  # fallback
    ],
)
def test__get_anytext_animations(monkeypatch, env_variable, value):  # type: ignore
    """Test that we parse the correct values from the env variable."""
    monkeypatch.setenv("ANYTEXT_ANIMATIONS", env_variable)
    assert _get_anytext_animations() == value


@pytest.mark.parametrize(
    ["value"],
    [("full",), ("basic",), ("none",)],
)
def test_app_show_animations(monkeypatch, value):  # type: ignore
    """Test that the app gets the value of `show_animations` correctly."""
    monkeypatch.setattr(constants, "ANYTEXT_ANIMATIONS", value)
    app = App()
    assert app.animation_level == value
