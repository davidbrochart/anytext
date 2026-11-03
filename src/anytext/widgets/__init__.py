from __future__ import annotations

import typing
from importlib import import_module

from anytext.case import camel_to_snake

# For any new built-in Widget we create, not only do we have to import them here and add them to `__all__`,
# but also to the `__init__.pyi` file in this same folder - otherwise text editors and type checkers won't
# be able to "see" them.
if typing.TYPE_CHECKING:
    from anytext.widget import Widget
    from anytext.widgets._button import Button
    from anytext.widgets._checkbox import Checkbox
    from anytext.widgets._collapsible import Collapsible
    from anytext.widgets._content_switcher import ContentSwitcher
    from anytext.widgets._data_table import DataTable
    from anytext.widgets._digits import Digits
    from anytext.widgets._directory_tree import DirectoryTree
    from anytext.widgets._footer import Footer
    from anytext.widgets._header import Header
    from anytext.widgets._help_panel import HelpPanel
    from anytext.widgets._input import Input
    from anytext.widgets._key_panel import KeyPanel
    from anytext.widgets._label import Label
    from anytext.widgets._link import Link
    from anytext.widgets._list_item import ListItem
    from anytext.widgets._list_view import ListView
    from anytext.widgets._loading_indicator import LoadingIndicator
    from anytext.widgets._log import Log
    from anytext.widgets._markdown import Markdown, MarkdownViewer
    from anytext.widgets._masked_input import MaskedInput
    from anytext.widgets._option_list import OptionList
    from anytext.widgets._placeholder import Placeholder
    from anytext.widgets._pretty import Pretty
    from anytext.widgets._progress_bar import ProgressBar
    from anytext.widgets._radio_button import RadioButton
    from anytext.widgets._radio_set import RadioSet
    from anytext.widgets._rich_log import RichLog
    from anytext.widgets._rule import Rule
    from anytext.widgets._select import Select
    from anytext.widgets._selection_list import SelectionList
    from anytext.widgets._sparkline import Sparkline
    from anytext.widgets._split_pane import SplitPane
    from anytext.widgets._static import Static
    from anytext.widgets._switch import Switch
    from anytext.widgets._tabbed_content import TabbedContent, TabPane
    from anytext.widgets._tabs import Tab, Tabs
    from anytext.widgets._text_area import TextArea
    from anytext.widgets._tooltip import Tooltip
    from anytext.widgets._tree import Tree
    from anytext.widgets._welcome import Welcome

__all__ = [
    "Button",
    "Checkbox",
    "Collapsible",
    "ContentSwitcher",
    "DataTable",
    "Digits",
    "DirectoryTree",
    "Footer",
    "Header",
    "HelpPanel",
    "Input",
    "KeyPanel",
    "Label",
    "Link",
    "ListItem",
    "ListView",
    "LoadingIndicator",
    "Log",
    "Markdown",
    "MarkdownViewer",
    "MaskedInput",
    "OptionList",
    "Placeholder",
    "Pretty",
    "ProgressBar",
    "RadioButton",
    "RadioSet",
    "RichLog",
    "Rule",
    "Select",
    "SelectionList",
    "Sparkline",
    "SplitPane",
    "Static",
    "Switch",
    "Tab",
    "TabbedContent",
    "TabPane",
    "Tabs",
    "TextArea",
    "Tooltip",
    "Tree",
    "Welcome",
]

_WIDGETS_LAZY_LOADING_CACHE: dict[str, type[Widget]] = {}


# Let's decrease startup time by lazy loading our Widgets:
def __getattr__(widget_class: str) -> type[Widget]:
    try:
        return _WIDGETS_LAZY_LOADING_CACHE[widget_class]
    except KeyError:
        pass

    if widget_class not in __all__:
        raise AttributeError(f"Package 'anytext.widgets' has no class '{widget_class}'")

    widget_module_path = f"._{camel_to_snake(widget_class)}"
    module = import_module(widget_module_path, package="anytext.widgets")
    class_ = getattr(module, widget_class)

    _WIDGETS_LAZY_LOADING_CACHE[widget_class] = class_
    return class_
