from __future__ import annotations

from anytext.app import App


async def test_anytext_env_var(monkeypatch):
    monkeypatch.setenv("ANYTEXT", "")
    app = App()
    assert app.features == set()
    assert app.devtools is None
    assert app.debug is False

    monkeypatch.setenv("ANYTEXT", "devtools")
    app = App()
    assert app.features == {"devtools"}
    assert app.devtools is not None
    assert app.debug is False

    monkeypatch.setenv("ANYTEXT", "devtools,debug")
    app = App()
    assert app.features == {"devtools", "debug"}
    assert app.devtools is not None
    assert app.debug is True

    monkeypatch.setenv("ANYTEXT", "devtools, debug")
    app = App()
    assert app.features == {"devtools", "debug"}
    assert app.devtools is not None
    assert app.debug is True
