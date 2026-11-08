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


def test_native_name_handling_has_no_compatibility_calls():
    run_isolated(
        """
        import sys
        from anytext import alias_textual, _compat_names
        from anytext._node_list import NodeList
        from anytext.dom import DOMNode
        from anytext.widgets import Static
        from anytext.css.parse import parse_selectors

        normalizers = {
            _compat_names.normalize_id.__code__,
            _compat_names.normalize_class.__code__,
            _compat_names.normalize_theme.__code__,
        }
        calls = []
        def profile(frame, event, arg):
            if event == 'call' and frame.f_code in normalizers:
                calls.append(frame.f_code.co_name)

        original_lookup = NodeList._get_by_id
        original_has_class = DOMNode.has_class
        sys.setprofile(profile)
        try:
            widget = Static(id='example', classes='example')
            widget.has_class('example')
            widget.add_class('other')
            widget.remove_class('other')
            widget.toggle_class('other')
            widget.update_classes({'other': False})
            widget.classes = 'example'
            NodeList()._get_by_id('example')
            parse_selectors('#example.example')
        finally:
            sys.setprofile(None)
        assert not calls, calls
        assert NodeList._get_by_id is original_lookup
        assert DOMNode.has_class is original_has_class

        alias_textual()
        assert NodeList._get_by_id is not original_lookup
        assert DOMNode.has_class is not original_has_class
        lookup, has_class = NodeList._get_by_id, DOMNode.has_class
        alias_textual()
        assert NodeList._get_by_id is lookup
        assert DOMNode.has_class is has_class
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
    (tmp_path / "legacy.tcss").write_text(
        ".-theme-textual-dark Label { color: #123456; }\n"
    )
    (tmp_path / "existing_library.py").write_text(
        dedent(
            """
        from textual.app import App, ComposeResult
        from textual.widgets import Label
        class ExistingApp(App):
            CSS_PATH = "legacy.tcss"
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


def test_css_name_compatibility_is_opt_in():
    run_isolated(
        """
        from anytext.app import App, InvalidThemeError
        from anytext.widgets import Static
        from anytext.css.parse import parse_selectors
        node = Static('content', id='textual-tooltip', classes='-textual-compact')
        assert node.id == 'textual-tooltip'
        assert node.classes == frozenset({'-textual-compact'})
        assert not node.has_class('-anytext-compact')
        selectors = parse_selectors('#textual-tooltip.-textual-compact')[0].selectors
        assert [selector.name for selector in selectors] == ['textual-tooltip', '-textual-compact']
        app = App()
        assert app.get_theme('textual-dark') is None
        try:
            app.theme = 'textual-light'
        except InvalidThemeError:
            pass
        else:
            raise AssertionError('Legacy theme names must require activation')
    """
    )


def test_aliasing_invalidates_cached_legacy_selectors():
    run_isolated(
        """
        from anytext.css.parse import parse_selectors
        before = parse_selectors('#textual-tooltip.-textual-system')[0].selectors
        assert [s.name for s in before] == ['textual-tooltip', '-textual-system']
        from anytext import alias_textual
        alias_textual()
        after = parse_selectors('#textual-tooltip.-textual-system')[0].selectors
        assert [s.name for s in after] == ['anytext-tooltip', '-anytext-system']
        # Activation must not mutate selector objects held by callers.
        assert [s.name for s in before] == ['textual-tooltip', '-textual-system']
    """
    )


@pytest.mark.parametrize(
    "legacy, canonical",
    [
        ("textual-tooltip", "anytext-tooltip"),
        ("textual-toastrack", "anytext-toastrack"),
        ("--textual-toast-example", "--anytext-toast-example"),
    ],
)
def test_legacy_id_construction_and_lookup(legacy, canonical):
    run_isolated(
        """
        import sys
        from anytext import alias_textual
        alias_textual()
        from textual.widgets import Static
        from textual.walk import walk_breadth_search_id
        legacy, canonical = sys.argv[1:]
        node = Static('content', id=legacy)
        assert node.id == canonical
        assert walk_breadth_search_id(node, legacy) is node
        other = Static('other')
        other.id = legacy
        assert other.id == canonical
    """,
        legacy,
        canonical,
    )


@pytest.mark.parametrize(
    "legacy, canonical",
    [
        ("-textual-system", "-anytext-system"),
        ("-textual-compact", "-anytext-compact"),
        ("-textual-loading-indicator", "-anytext-loading-indicator"),
        ("--textual-command-palette", "--anytext-command-palette"),
        ("-theme-textual-dark", "-theme-anytext-dark"),
        ("-theme-textual-light", "-theme-anytext-light"),
    ],
)
def test_legacy_class_mutations_use_canonical_storage(legacy, canonical):
    run_isolated(
        """
        import sys
        from anytext import alias_textual
        alias_textual()
        from textual.widgets import Static
        legacy, canonical = sys.argv[1:]
        node = Static('content', classes=legacy)
        assert node.classes == frozenset({canonical})
        assert node.has_class(legacy, canonical)
        node.remove_class(legacy)
        assert not node.has_class(canonical)
        node.add_class(legacy)
        assert node.has_class(canonical)
        node.toggle_class(legacy)
        assert not node.has_class(canonical)
        node.set_class(True, legacy)
        assert node.has_class(canonical)
        node.update_classes({legacy: False})
        assert not node.has_class(canonical)
        node.update_classes({legacy: True})
        assert node.has_class(canonical)
        node.set_classes([legacy])
        assert node.classes == frozenset({canonical})
        node.classes = legacy + ' my-textual-custom'
        assert node.classes == frozenset({canonical, 'my-textual-custom'})
    """,
        legacy,
        canonical,
    )


def test_legacy_tcss_and_queries_work_without_changing_user_files(tmp_path):
    css = """
    /* textual-tooltip remains in this comment and in the unused string. */
    $caption: "textual-tooltip";
    $my-textual-color: #123456;
    #textual-tooltip { color: $my-textual-color; }
    #textual-toastrack { padding: 1; }
    .-theme-textual-light #my-textual-panel { color: #ABCDEF; }
    .-theme-textual-dark #my-textual-panel { color: #FEDCBA; }
    #my-textual-panel.project-textual-class { background: #234567; }
    """
    css_path = tmp_path / "textual-tooltip.tcss"
    css_path.write_text(css)
    run_isolated(
        """
        import sys
        import anyio
        from pathlib import Path
        from anytext import alias_textual
        alias_textual()
        from textual import on
        from textual.app import App
        from textual.widget import Widget
        from textual.widgets import Button, Label
        class LegacyWidget(Widget):
            DEFAULT_CSS = '''
            LegacyWidget {
                Button {
                    &.-textual-compact { background: #2468AC; }
                }
            }
            '''
            def compose(self):
                yield Button('Compact', compact=True)
        class ExistingApp(App):
            CSS_PATH = sys.argv[1]
            handled = False
            @on(Button.Pressed, '.-textual-compact')
            def compact_pressed(self):
                self.handled = True
            def compose(self):
                yield Label('my-textual-content', id='my-textual-panel', classes='project-textual-class')
                yield LegacyWidget()
            def on_mount(self):
                self.theme = 'textual-light'
        async def main():
            app = ExistingApp()
            async with app.run_test(tooltips=True, notifications=True) as pilot:
                label = app.query_one('#my-textual-panel')
                button = app.query_one('Button.-textual-compact')
                tooltip = app.screen.query_one('#textual-tooltip')
                toasts = app.screen.query_one('#textual-toastrack')
                assert app.screen.get_child_by_id('textual-tooltip') is tooltip
                assert app.screen.get_widget_by_id('textual-tooltip') is tooltip
                assert app.get_widget_by_id('textual-toastrack') is toasts
                assert app.query_one('#anytext-tooltip') is tooltip
                assert tooltip.id == 'anytext-tooltip'
                assert tooltip.has_class('-textual-system')
                assert list(app.query('.-textual-system')) == list(app.query('.-anytext-system'))
                assert app.query_one('LegacyWidget > Button.-textual-compact') is button
                assert list(app.query('Button').filter('.-textual-compact')) == [button]
                with anyio.fail_after(5):
                    while label.styles.color.hex != '#ABCDEF':
                        await pilot.pause()
                        await anyio.sleep(.01)
                assert label.styles.background.hex == '#234567'
                assert button.styles.background.hex == '#2468AC'
                await pilot.click(button)
                assert app.handled
                assert tooltip.styles.color.hex == '#123456'
                assert toasts.styles.padding == (1, 1, 1, 1)
                assert str(label.content) == 'my-textual-content'
                assert label.id == 'my-textual-panel'
                assert label.has_class('project-textual-class')
                assert app.theme == 'anytext-light'
                assert app.has_class('-theme-textual-light')
                app.action_toggle_dark()
                with anyio.fail_after(5):
                    while label.styles.color.hex != '#FEDCBA':
                        await pilot.pause()
                        await anyio.sleep(.01)
                assert app.theme == 'anytext-dark'
        anyio.run(main)
    """,
        str(css_path),
    )
    assert css_path.read_text() == css


def test_theme_aliases_cover_lookup_registration_and_removal():
    run_isolated(
        """
        from anytext import alias_textual
        alias_textual()
        from textual.app import App
        from textual.theme import Theme
        app = App()
        assert app.get_theme('missing, textual-dark') is app.get_theme('anytext-dark')
        assert app.get_theme('textual-light') is app.get_theme('anytext-light')
        original = Theme(name='textual-dark', primary='#123456')
        app.register_theme(original)
        assert original.name == 'textual-dark'
        assert app.get_theme('textual-dark').name == 'anytext-dark'
        assert app.get_theme('textual-dark').primary == '#123456'
        app.theme = 'textual-dark'
        assert app.theme == 'anytext-dark'
        app.unregister_theme('textual-dark')
        assert app.get_theme('anytext-dark') is None
        custom = Theme(name='textual-custom', primary='#abcdef')
        app.register_theme(custom)
        assert app.get_theme('textual-custom') is custom
        app.theme = 'textual-custom'
        assert app.theme == 'textual-custom'
    """
    )
