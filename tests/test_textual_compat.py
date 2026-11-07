"""Compatibility must work in a fresh process before Textual is imported."""

import os
import subprocess
import sys
from textwrap import dedent

import pytest


def run_isolated(source, *args, cwd=None, env=None):
    result = subprocess.run(
        [sys.executable, "-c", dedent(source), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def test_importing_compat_does_not_activate_aliases():
    run_isolated(
        """
        import sys
        from anytext import alias_textual
        assert not any(n == 'textual' or n.startswith('textual.') for n in sys.modules)
        assert not any(type(f).__name__ == '_TextualAliasFinder' for f in sys.meta_path)
    """
    )


def test_preloaded_modules_and_idempotent_setup():
    run_isolated(
        """
        import sys
        import anytext.app
        import anytext.widgets
        from anytext import alias_textual
        metadata = anytext.app.__spec__, anytext.app.__loader__, anytext.app.__package__
        alias_textual()
        from anytext.compat import alias_textual as compatibility_alias
        compatibility_alias()
        finders = list(sys.meta_path)
        alias_textual()
        assert sys.meta_path == finders
        import textual
        from textual.app import App
        from textual.widgets import Button
        assert textual is sys.modules['anytext']
        assert App is anytext.app.App
        assert Button is anytext.widgets.Button
        assert (anytext.app.__spec__, anytext.app.__loader__, anytext.app.__package__) == metadata
        assert sys.modules['textual._context'] is sys.modules['anytext._context']
    """
    )


@pytest.mark.parametrize("alias_first", [False, True])
def test_submodules_preserve_identity_metadata_and_resources(alias_first):
    run_isolated(
        """
        import importlib
        import sys
        from importlib.resources import files
        from anytext import alias_textual
        alias_textual()
        alias_first = sys.argv[1] == 'True'
        for suffix in ['app', 'widgets', 'widgets._button', 'document._document',
                       'drivers.callback_driver', 'css.styles', 'compat']:
            names = ['textual.' + suffix, 'anytext.' + suffix]
            if not alias_first:
                names.reverse()
            first = importlib.import_module(names[0])
            metadata = first.__name__, first.__package__, first.__spec__, first.__loader__
            second = importlib.import_module(names[1])
            assert first is second
            assert (second.__name__, second.__package__, second.__spec__, second.__loader__) == metadata
            assert second.__spec__.name == 'anytext.' + suffix
        assert files('textual').joinpath('py.typed').is_file()
        assert files('textual.widgets').joinpath('_button.py').is_file()
        from textual.widgets import Button, SplitPane
        from anytext.widgets import Button as AnytextButton, SplitPane as AnytextSplitPane
        assert Button is AnytextButton
        assert SplitPane is AnytextSplitPane
        from textual._context import active_app
        from anytext._context import active_app as canonical_context
        assert active_app is canonical_context
    """,
        str(alias_first),
    )


def test_renamed_public_symbols_share_the_anytext_classes():
    run_isolated(
        """
        from anytext import alias_textual, errors, logging
        assert not hasattr(errors, 'TextualError')
        assert not hasattr(logging, 'TextualHandler')
        alias_textual()
        from textual.errors import TextualError, NoWidget
        from textual.logging import TextualHandler
        from textual import logging as legacy_logging
        assert TextualError is errors.AnytextError
        assert issubclass(NoWidget, TextualError)
        assert TextualHandler is logging.AnytextHandler
        assert legacy_logging.TextualHandler is logging.AnytextHandler
    """
    )


def test_module_discovery_keeps_lazy_imports_lazy():
    run_isolated(
        """
        import sys
        from importlib.util import find_spec
        from anytext import alias_textual
        alias_textual()
        assert 'anytext.widgets._sparkline' not in sys.modules
        spec = find_spec('textual.widgets._sparkline')
        assert spec is not None
        assert spec.name == 'textual.widgets._sparkline'
        assert 'anytext.widgets._sparkline' not in sys.modules
        assert 'textual.widgets._sparkline' not in sys.modules
        assert find_spec('textual.missing_compat_module') is None
    """
    )


@pytest.mark.parametrize("name", ["textual", "textual.app"])
def test_setup_rejects_real_textual_without_replacing_it(name):
    run_isolated(
        """
        import importlib
        import sys
        importlib.import_module(sys.argv[1])
        from anytext import alias_textual
        original = {n: m for n, m in sys.modules.items() if n == 'textual' or n.startswith('textual.')}
        finders = list(sys.meta_path)
        try:
            alias_textual()
        except RuntimeError as error:
            assert 'before importing Textual' in str(error)
        else:
            raise AssertionError('Loading real Textual first must be rejected')
        assert sys.meta_path == finders
        assert all(sys.modules[n] is m for n, m in original.items())
    """,
        name,
    )


def test_setup_rejects_partial_or_blocked_textual_imports():
    run_isolated(
        """
        import sys
        from types import ModuleType
        from anytext import alias_textual
        for name, module in [('textual.app', ModuleType('textual.app')), ('textual', None)]:
            sys.modules[name] = module
            try:
                alias_textual()
            except RuntimeError:
                pass
            else:
                raise AssertionError('Conflicting imports must be rejected')
            assert sys.modules[name] is module
            del sys.modules[name]
        alias_textual()
    """
    )


def test_missing_submodule_uses_alias_name_and_keeps_dependency_errors(tmp_path):
    (tmp_path / "needs_dependency.py").write_text("import missing_compat_dependency\n")
    run_isolated(
        """
        import importlib
        import sys
        import anytext
        from anytext import alias_textual
        alias_textual()
        try:
            importlib.import_module('textual.missing_compat_module')
        except ModuleNotFoundError as error:
            assert error.name == 'textual.missing_compat_module'
        else:
            raise AssertionError('A missing module must fail')
        anytext.__path__.append(sys.argv[1])
        try:
            importlib.import_module('textual.needs_dependency')
        except ModuleNotFoundError as error:
            assert error.name == 'missing_compat_dependency'
        else:
            raise AssertionError('A missing dependency must fail')
    """,
        str(tmp_path),
    )


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_textual_app_runs_with_shared_context_without_threads(backend):
    run_isolated(
        """
        import sys
        import anyio
        from anytext import alias_textual
        alias_textual()
        from textual import on
        from textual.app import App, ComposeResult
        from textual.widgets import Button, Label
        from anytext.app import App as AnytextApp
        from anytext._context import active_app
        class ExistingLibraryApp(App):
            def compose(self) -> ComposeResult:
                yield Button('Press', id='press')
                yield Label('Before', id='result')
            @on(Button.Pressed, '#press')
            def pressed(self):
                self.query_one('#result', Label).update('After')
        async def main():
            import socket
            def forbidden(*args, **kwargs):
                raise AssertionError('Compatibility setup must not require threads or socket pairs')
            anyio.to_thread.run_sync = forbidden
            socket.socketpair = forbidden
            app = ExistingLibraryApp()
            assert isinstance(app, AnytextApp)
            async with app.run_test() as pilot:
                assert active_app.get() is app
                assert app._runtime.portal is None
                await pilot.click('#press')
                assert str(app.query_one('#result', Label).content) == 'After'
        anyio.run(main, backend=sys.argv[1])
    """,
        backend,
        env={**os.environ, "ANYTEXT_THREADS": "0"},
    )


def test_unmodified_snapshot_plugin_accepts_anytext_apps(tmp_path):
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    (tmp_path / "existing_library.py").write_text(
        dedent(
            """
        from textual.app import App, ComposeResult
        from textual.widgets import Label
        class ExistingApp(App):
            def compose(self) -> ComposeResult:
                yield Label('An unchanged Textual app')
    """
        )
    )
    (tmp_path / "test_existing_library.py").write_text(
        dedent(
            """
        from existing_library import ExistingApp
        def test_app_instance(snap_compare):
            assert snap_compare(ExistingApp())
        def test_app_file(snap_compare):
            assert snap_compare('existing_library.py')
    """
        )
    )
    source = """
        import sys
        from anytext import alias_textual
        alias_textual()
        import pytest
        raise SystemExit(pytest.main([
            '-c', 'pytest.ini', '-p', 'syrupy', '-p', 'pytest_textual_snapshot',
            '-q', 'test_existing_library.py', *sys.argv[1:]
        ]))
    """
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("PYTEST_XDIST_") and name != "TEXTUAL_SNAPSHOT_TEMPDIR"
    }
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    run_isolated(source, "--snapshot-update", cwd=tmp_path, env=env)
    run_isolated(source, cwd=tmp_path, env=env)
    assert len(list(tmp_path.rglob("*.svg"))) == 2
