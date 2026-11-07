"""Install legacy name handling only when Textual aliasing is enabled."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import replace
from functools import wraps
from typing import Any

from typing_extensions import Self

from anytext import dom, walk
from anytext._node_list import NodeList
from anytext.app import App
from anytext.css import parse as css_parse
from anytext.dom import DOMNode, _ClassesDescriptor
from anytext.theme import Theme
from anytext.widget import Widget

# Some of these types also resolve annotations copied by functools.wraps.
__all__: list[str] = []
enabled = False

_ID_ALIASES = {
    "textual-tooltip": "anytext-tooltip",
    "textual-toastrack": "anytext-toastrack",
}
_CLASS_ALIASES = {
    "-textual-system": "-anytext-system",
    "-textual-compact": "-anytext-compact",
    "-textual-loading-indicator": "-anytext-loading-indicator",
    "--textual-command-palette": "--anytext-command-palette",
    "-theme-textual-dark": "-theme-anytext-dark",
    "-theme-textual-light": "-theme-anytext-light",
}
_THEME_ALIASES = {
    "textual-dark": "anytext-dark",
    "textual-light": "anytext-light",
}


def normalize_id(name: str) -> str:
    if not enabled:
        return name
    if name.startswith("--textual-toast-"):
        return "--anytext-toast-" + name[len("--textual-toast-") :]
    return _ID_ALIASES.get(name, name)


def normalize_class(name: str) -> str:
    return _CLASS_ALIASES.get(name, name) if enabled else name


def normalize_theme(name: str) -> str:
    return _THEME_ALIASES.get(name, name) if enabled else name


def _get_by_id_compatible(self: NodeList, widget_id: str) -> Widget | None:
    return self._nodes_by_id.get(normalize_id(widget_id))


def _wrap_classes(method):
    @wraps(method)
    def with_aliases(self, *class_names: str, **kwargs: Any):
        return method(self, *(normalize_class(name) for name in class_names), **kwargs)

    return with_aliases


def _wrap_theme_name(method):
    @wraps(method)
    def with_aliases(self, theme_name: str):
        return method(self, normalize_theme(theme_name))

    return with_aliases


def _install_dom_hooks() -> None:
    init = DOMNode.__init__

    @wraps(init)
    def init_with_aliases(self, *args: Any, **kwargs: Any):
        if kwargs.get("id") is not None:
            kwargs["id"] = normalize_id(kwargs["id"])
        if kwargs.get("classes") is not None:
            kwargs["classes"] = " ".join(
                normalize_class(name) for name in kwargs["classes"].split()
            )
        init(self, *args, **kwargs)

    id_property = DOMNode.id
    set_id = id_property.fset

    @wraps(set_id)
    def set_id_with_aliases(self, new_id: str):
        return set_id(self, normalize_id(new_id))

    set_classes = _ClassesDescriptor.__set__

    @wraps(set_classes)
    def set_classes_with_aliases(self, obj: DOMNode, classes: str | Iterable[str]):
        names = classes.split() if isinstance(classes, str) else classes
        set_classes(self, obj, tuple(normalize_class(name) for name in names))

    update_classes = DOMNode.update_classes

    @wraps(update_classes)
    def update_classes_with_aliases(
        self, classes: Mapping[str, bool], update: bool = True, animate: bool = True
    ):
        classes = {normalize_class(name): add for name, add in classes.items()}
        return update_classes(self, classes, update=update, animate=animate)

    search_id = walk.walk_breadth_search_id

    @wraps(search_id)
    def search_id_with_aliases(root: DOMNode, node_id: str, *, with_root: bool = True):
        return search_id(root, normalize_id(node_id), with_root=with_root)

    DOMNode.__init__ = init_with_aliases
    DOMNode.id = id_property.setter(set_id_with_aliases)
    _ClassesDescriptor.__set__ = set_classes_with_aliases
    DOMNode.update_classes = update_classes_with_aliases
    for name in ("has_class", "add_class", "remove_class", "toggle_class"):
        setattr(DOMNode, name, _wrap_classes(getattr(DOMNode, name)))
    NodeList._get_by_id = wraps(NodeList._get_by_id)(_get_by_id_compatible)
    walk.walk_breadth_search_id = search_id_with_aliases
    # DOM queries hold an imported reference to the walking helper.
    dom.walk_breadth_search_id = search_id_with_aliases


def _install_css_hook() -> None:
    tokenize = css_parse.tokenize

    @wraps(tokenize)
    def tokenize_with_aliases(*args: Any, **kwargs: Any):
        for token in tokenize(*args, **kwargs):
            value = token.value
            if token.name in {"selector_id", "selector_start_id"}:
                value = "#" + normalize_id(value[1:])
            elif token.name in {"selector_class", "selector_start_class"}:
                value = "." + normalize_class(value[1:])
            if value != token.value:
                token = token._replace(value=value)
            yield token

    # Both query parsing and stylesheet parsing look this up at call time.
    # Declaration tokens and the original source/code locations are preserved.
    css_parse.tokenize = tokenize_with_aliases
    css_parse.parse_selectors.cache_clear()


def _install_theme_hooks() -> None:
    get_theme = App.get_theme

    @wraps(get_theme)
    def get_theme_with_aliases(self, theme_name: str):
        names = (normalize_theme(name.strip()) for name in theme_name.split(","))
        return get_theme(self, ",".join(names))

    register_theme = App.register_theme

    @wraps(register_theme)
    def register_theme_with_aliases(self, theme: Theme):
        name = normalize_theme(theme.name)
        if name != theme.name:
            theme = replace(theme, name=name)
        register_theme(self, theme)

    App.get_theme = get_theme_with_aliases
    App.register_theme = register_theme_with_aliases
    App.unregister_theme = _wrap_theme_name(App.unregister_theme)
    App._validate_theme = _wrap_theme_name(App._validate_theme)


def enable() -> None:
    """Install compatibility hooks once; native paths stay untouched otherwise."""
    global enabled
    if enabled:
        return
    _install_dom_hooks()
    _install_css_hook()
    _install_theme_hooks()
    enabled = True
