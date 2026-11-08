# Using libraries written for Textual

Call `alias_textual()` at application startup to make imports of `textual` and
its submodules resolve to Anytext. Third-party libraries can keep their existing
Textual imports.

```python
from anytext import alias_textual

alias_textual()

# This library can continue to import textual.app, textual.widgets, etc.
import your_textual_library
```

Activation is explicit and applies to the whole Python process. Applications
choose whether to activate it; reusable libraries should leave that decision to
their caller. Importing Anytext alone does not activate aliases.

## Shared classes and application state

Both names refer to the same module objects and classes:

```python
from anytext import alias_textual

alias_textual()

from textual.app import App
from anytext.app import App as AnytextApp

assert App is AnytextApp
```

Lazy widget imports, message types, and application contexts are shared too.
This avoids loading two independent frameworks when an application imports
Anytext and a dependency imports Textual. The public names `TextualError` and
`TextualHandler` also become aliases for `AnytextError` and `AnytextHandler`.

Anytext remains the canonical module name: `App.__module__` is `"anytext.app"`,
module metadata and resource paths refer to Anytext, and `textual.__version__`
reports the Anytext version.

## CSS, DOM queries, and themes

Activation also accepts the framework-owned CSS names renamed by Anytext:

| Legacy name | Canonical Anytext name |
| --- | --- |
| `#textual-tooltip` | `#anytext-tooltip` |
| `#textual-toastrack` | `#anytext-toastrack` |
| `#--textual-toast-<identity>` | `#--anytext-toast-<identity>` |
| `.-textual-system` | `.-anytext-system` |
| `.-textual-compact` | `.-anytext-compact` |
| `.-textual-loading-indicator` | `.-anytext-loading-indicator` |
| `.--textual-command-palette` | `.--anytext-command-palette` |
| `.-theme-textual-dark` | `.-theme-anytext-dark` |
| `.-theme-textual-light` | `.-theme-anytext-light` |

These mappings apply to inline and external TCSS, including nested selectors,
DOM queries, selector-based event handlers, and class helpers such as
`has_class()`, `add_class()`, and `remove_class()`. ID lookups such as
`query_one("#textual-tooltip")` and `get_widget_by_id("textual-tooltip")` return the
same widget as the canonical names. Supplying a reserved legacy ID or class
when constructing a widget stores its canonical Anytext name.

The default theme aliases work for selection, lookup, registration, and removal:

```python
app.theme = "textual-light"
assert app.theme == "anytext-light"
assert app.get_theme("textual-dark") is app.get_theme("anytext-dark")
```

Widget IDs, class sets, and active theme names remain canonical when read back.
Only the listed framework-owned names are mapped. Custom names such as
`my-textual-panel` and `textual-custom` are unchanged. Stylesheet files, comments,
strings, CSS variables, and resource paths are not rewritten.

## Startup order

Call `alias_textual()` **before importing Textual or libraries that import it**.
Compatibility hooks are installed only by this call. Normal Anytext usage keeps
the original ID, class, theme, and CSS parsing paths without normalization overhead.
Enable it before constructing widgets or loading stylesheets as well. Cached
selector parses are cleared at activation; existing widget trees are not migrated.
If real Textual modules are already loaded, activation raises `RuntimeError`
without replacing them. Restart the process and move activation earlier.
Already imported Anytext modules are supported, and repeated activation is safe.
There is no deactivation operation; use a separate process when both framework
implementations need to run independently.

For pytest plugins that import Textual during startup, activate the alias before
starting pytest, rather than in a fixture:

```python
from anytext import alias_textual

alias_textual()

import pytest

raise SystemExit(pytest.main())
```

## Scope

This aliases imports; it does not change dependency resolution or installed
package metadata. If a dependency declares `textual`, pip or uv may still install
that distribution. Activating the alias makes its Python imports use Anytext.
`importlib.metadata.version("textual")` still reads installed Textual metadata.

Environment settings continue to use `ANYTEXT_*` names. This does not install
Textual command-line entry points. Aliasing does not implement newer or removed Textual
APIs, nor change a library's assumptions about asyncio. Third-party libraries
using private framework internals should be checked individually. Libraries that
require asyncio should run with Anytext's asyncio backend.
