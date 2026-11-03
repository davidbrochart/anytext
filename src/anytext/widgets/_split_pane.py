"""Two panes with a mouse- and keyboard-resizable divider."""

from __future__ import annotations

from math import isfinite
from typing import ClassVar, Iterator, Literal

from anytext import events
from anytext.binding import Binding, BindingType
from anytext.geometry import Offset
from anytext.message import Message
from anytext.reactive import reactive
from anytext.widget import Widget

SplitOrientation = Literal["horizontal", "vertical"]


class _SplitPaneContent(Widget):
    """Keep pane sizing independent of the supplied widget's styles."""

    DEFAULT_CSS = """
    _SplitPaneContent {
        layer: split-panes;
        width: 1fr;
        height: 1fr;
        min-width: 0;
        min-height: 0;
        overflow: hidden hidden;
    }
    """


class _SplitPaneDivider(Widget, can_focus=True):
    ALLOW_SELECT = False
    DEFAULT_CSS = """
    _SplitPaneDivider {
        layer: split-panes;
        width: 1;
        height: 1fr;
        min-width: 0;
        min-height: 0;
        color: $primary;
        background: $surface;
        pointer: ew-resize;
        &.-vertical {
            width: 1fr;
            height: 1;
            pointer: ns-resize;
        }
        &:hover, &:focus, &.-dragging {
            color: $text;
            background: $primary;
        }
    }
    """
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("left", "resize('horizontal', -1)", show=False),
        Binding("right", "resize('horizontal', 1)", show=False),
        Binding("up", "resize('vertical', -1)", show=False),
        Binding("down", "resize('vertical', 1)", show=False),
        Binding("home", "limit(False)", show=False),
        Binding("end", "limit(True)", show=False),
        Binding("enter", "reset", show=False),
        Binding("escape", "cancel", show=False),
    ]

    def __init__(self, split_pane: SplitPane) -> None:
        super().__init__(classes="split-pane--divider")
        self.split_pane = split_pane
        self._drag_origin: Offset | None = None
        self._drag_size = 0
        self._drag_position = 0.5
        self.tooltip = "Drag to resize; arrows adjust, Enter resets"

    def render(self) -> str:
        if self.split_pane.orientation == "horizontal":
            return "\n".join("│" for _ in range(self.size.height))
        return "─" * self.size.width

    @property
    def _rendering_enabled(self) -> bool:
        # A hit-test-only handle must not add compositor cuts either: a cut
        # through a wide character would replace it with spaces.
        return self.split_pane.show_divider

    def cancel_drag(self) -> None:
        self._drag_origin = None
        self.remove_class("-dragging")
        if self.is_mounted:
            self.release_mouse()

    def _resize_to_mouse(self, event: events.MouseEvent) -> None:
        if self._drag_origin is not None:
            delta = event.screen_offset - self._drag_origin
            distance = (
                delta.x if self.split_pane.orientation == "horizontal" else delta.y
            )
            self.split_pane._set_first_size(self._drag_size + distance)

    def _on_mouse_down(self, event: events.MouseDown) -> None:
        if event.button != 1:
            return
        event.stop()
        event.prevent_default()
        self.focus()
        self._drag_origin = event.screen_offset
        self._drag_size = self.split_pane.first_size
        self._drag_position = self.split_pane.position
        self.add_class("-dragging")
        self.capture_mouse()

    def _on_mouse_move(self, event: events.MouseMove) -> None:
        if self._drag_origin is not None:
            event.stop()
            event.prevent_default()
            self._resize_to_mouse(event)

    def _on_mouse_up(self, event: events.MouseUp) -> None:
        if self._drag_origin is not None:
            event.stop()
            event.prevent_default()
            self._resize_to_mouse(event)
            self.cancel_drag()

    def _on_mouse_release(self) -> None:
        if self.app.mouse_captured is not self:
            self._drag_origin = None
            self.remove_class("-dragging")

    def _on_blur(self) -> None:
        self.cancel_drag()

    def _on_unmount(self) -> None:
        self.cancel_drag()

    def _on_click(self, event: events.Click) -> None:
        event.stop()
        event.prevent_default()

    def action_resize(self, orientation: str, distance: int) -> None:
        if orientation == self.split_pane.orientation:
            self.split_pane._set_first_size(self.split_pane.first_size + distance)

    def action_limit(self, end: bool) -> None:
        self.split_pane._set_first_size(self.split_pane._available if end else 0)

    def action_reset(self) -> None:
        self.split_pane.position = self.split_pane._initial_position

    def action_cancel(self) -> None:
        if self._drag_origin is not None:
            self.split_pane.position = self._drag_position
            self.cancel_drag()
        else:
            self.blur()


class SplitPane(Widget):
    """Two widgets separated by a draggable, keyboard-focusable divider.

    Horizontal splits place panes side by side; vertical splits stack them.
    ``position`` is the preferred fraction of available space for the first
    pane. Minimum sizes are measured in columns or rows, excluding the divider.
    Nest SplitPane instances to build layouts with more than two panes.
    """

    DEFAULT_CSS = """
    SplitPane {
        layers: split-panes split-divider;
        width: 1fr;
        height: 1fr;
        min-width: 0;
        min-height: 0;
        layout: horizontal;
        overflow: hidden hidden;
        &.-vertical { layout: vertical; }
    }
    """
    orientation: reactive[SplitOrientation] = reactive("horizontal", init=False)
    """Pane layout: horizontal (side by side) or vertical (stacked)."""
    position: reactive[float] = reactive(0.5, init=False)
    """Preferred first-pane fraction, between zero and one."""
    show_divider: reactive[bool] = reactive(True, init=False)
    """Show a one-cell divider, or use an invisible boundary with no layout gap."""
    min_first: reactive[int] = reactive(1, init=False)
    """Minimum first-pane size in cells."""
    min_second: reactive[int] = reactive(1, init=False)
    """Minimum second-pane size in cells."""

    class Changed(Message):
        """The actual pane sizes changed, including after a container resize."""

        def __init__(self, split_pane: SplitPane) -> None:
            super().__init__()
            self.split_pane = split_pane
            self.first_size = split_pane.first_size
            self.second_size = split_pane.second_size
            self.position = self.first_size / max(1, self.first_size + self.second_size)

        @property
        def control(self) -> SplitPane:
            return self.split_pane

    def __init__(
        self,
        first: Widget,
        second: Widget,
        *,
        orientation: SplitOrientation = "horizontal",
        position: float = 0.5,
        show_divider: bool = True,
        min_first: int = 1,
        min_second: int = 1,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        """Create a split with two content widgets and an initial split ratio."""
        if first is second:
            raise ValueError("SplitPane requires two distinct widgets")
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.first = first
        self.second = second
        self._first_pane = _SplitPaneContent(first, classes="split-pane--first")
        self._second_pane = _SplitPaneContent(second, classes="split-pane--second")
        self._divider = _SplitPaneDivider(self)
        self._first_size = self._second_size = self._available = 0
        self._last_content_size = self.content_size
        self._initial_position = self.validate_position(position)
        self.orientation = orientation
        self.position = position
        self.show_divider = show_divider
        self.min_first = min_first
        self.min_second = min_second

    @property
    def divider(self) -> Widget:
        """The focusable divider widget, e.g. for setting initial focus."""
        return self._divider

    @property
    def first_size(self) -> int:
        """Current first-pane size in cells along the split axis."""
        return self._first_size

    @property
    def second_size(self) -> int:
        """Current second-pane size in cells along the split axis."""
        return self._second_size

    def compose(self) -> Iterator[Widget]:
        yield self._first_pane
        yield self._divider
        yield self._second_pane

    def validate_orientation(self, orientation: SplitOrientation) -> SplitOrientation:
        if orientation not in {"horizontal", "vertical"}:
            raise ValueError("orientation must be 'horizontal' or 'vertical'")
        return orientation

    def validate_position(self, position: float) -> float:
        if not isfinite(position) or not 0 <= position <= 1:
            raise ValueError("position must be a finite fraction between zero and one")
        return float(position)

    def validate_min_first(self, minimum: int) -> int:
        if not isinstance(minimum, int) or minimum < 0:
            raise ValueError("min_first must be a nonnegative integer")
        return minimum

    def validate_min_second(self, minimum: int) -> int:
        if not isinstance(minimum, int) or minimum < 0:
            raise ValueError("min_second must be a nonnegative integer")
        return minimum

    def watch_orientation(self) -> None:
        self._divider.cancel_drag()
        vertical = self.orientation == "vertical"
        self.set_class(vertical, "-vertical")
        self._divider.set_class(vertical, "-vertical")
        self._divider.refresh()
        self._update_sizes()

    def watch_show_divider(self) -> None:
        self._divider.cancel_drag()
        self._divider.styles.position = "relative" if self.show_divider else "absolute"
        self._divider.styles.layer = (
            "split-panes" if self.show_divider else "split-divider"
        )
        self._divider.refresh()
        self._update_sizes()

    def watch_position(self) -> None:
        self._update_sizes()

    def watch_min_first(self) -> None:
        self._update_sizes()

    def watch_min_second(self) -> None:
        self._update_sizes()

    def watch_disabled(self, disabled: bool) -> None:
        super().watch_disabled(disabled)
        if disabled and hasattr(self, "_divider"):
            self._divider.cancel_drag()

    def _on_mount(self) -> None:
        self._update_sizes()

    def _on_resize(self) -> None:
        size = self.content_size
        if size != self._last_content_size:
            self._divider.cancel_drag()
        self._last_content_size = size
        self._update_sizes()

    def _available_space(self) -> int:
        size = self.content_size
        return max(
            0,
            (size.width if self.orientation == "horizontal" else size.height)
            - int(self.show_divider),
        )

    def _limits(self, available: int) -> tuple[int, int]:
        minimum = self.min_first + self.min_second
        if minimum > available:
            # Impossible minima: share the remaining space proportionally rather
            # than overflowing the container or producing negative dimensions.
            first = round(available * self.min_first / minimum)
            return first, first
        return self.min_first, available - self.min_second

    def _set_first_size(self, size: int) -> None:
        available = self._available_space()
        if available:
            low, high = self._limits(available)
            first = max(low, min(high, size))
            if first != self.first_size:
                self.position = first / available

    def _update_sizes(self) -> None:
        if not self.is_mounted:
            return
        available = self._available_space()
        low, high = self._limits(available)
        first = max(low, min(high, round(available * self.position)))
        second = available - first
        previous = (self._first_size, self._second_size)
        self._first_size, self._second_size, self._available = first, second, available
        if self.orientation == "horizontal":
            self._first_pane.styles.width = first
            self._second_pane.styles.width = second
            self._first_pane.styles.height = self._second_pane.styles.height = "1fr"
        else:
            self._first_pane.styles.height = first
            self._second_pane.styles.height = second
            self._first_pane.styles.width = self._second_pane.styles.width = "1fr"
        if self.show_divider:
            self._divider.styles.offset = (0, 0)
        else:
            edge = max(0, first - 1)
            self._divider.styles.offset = (
                (edge, 0) if self.orientation == "horizontal" else (0, edge)
            )
        if previous != (first, second):
            self.post_message(self.Changed(self))
