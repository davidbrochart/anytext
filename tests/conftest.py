"""Adapters for external test tools which still target the upstream package."""

from __future__ import annotations

import pytest


@pytest.fixture
def snap_compare(snap_compare, monkeypatch):
    """Let the upstream snapshot plugin load Anytext apps as well as its previews.

    Keep its snapshot format and HTML reports, but use our app loader for our
    examples. The upstream developer-tool previews remain upstream apps.
    """
    import pytest_textual_snapshot
    from textual import _import_app as upstream_import
    from textual._import_app import import_app as import_upstream_app
    from textual.app import App as UpstreamApp

    from anytext._import_app import AppFail, import_app
    from anytext.app import App

    def load_app(path):
        try:
            return import_app(path)
        except AppFail:
            return import_upstream_app(path)

    monkeypatch.setattr(pytest_textual_snapshot, "App", (App, UpstreamApp))
    monkeypatch.setattr(upstream_import, "import_app", load_app)
    return snap_compare
