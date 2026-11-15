"""Two panes with a mouse- and keyboard-resizable divider."""

from __future__ import annotations

from math import isfinite
from typing import ClassVar, Iterator, Literal

from anytext import errors, events
from anytext.binding import Binding, BindingType
from anytext.geometry import Offset, Size
from anytext.message import Message
from anytext.reactive import reactive
from anytext.strip import Strip
from anytext.widget import Widget
from anytext.widgets._floating_window import FloatingWindow

SplitOrientation = Literal["horizontal", "vertical"]
PaneSide = Literal["first", "second"]
DragModifier = Literal["alt", "ctrl", "shift"]


class _PaneDragPreview(FloatingWindow, can_focus=False):
    """Paint a frozen pane while its live widget remains mounted."""

    ALLOW_SELECT = False
    DEFAULT_CSS = """
    _PaneDragPreview {
        border: none;
        padding: 0;
        min-width: 1;
        min-height: 1;
        overlay: screen;
    }
    """

    def __init__(self, strips: list[Strip]) -> None:
        super().__init__(movable=False, resizable=False)
        self._strips = strips

    def render_line(self, y: int) -> Strip:
        """Preserve the pane's rendered colors and text during the drag."""
        return (
            self._strips[y] if y < len(self._strips) else Strip.blank(self.size.width)
        )


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
        &.-drag-source { opacity: 35%; }
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
        self._drag_button = 1
        self._drag_position = 0.5
        self._drag_targets: list[tuple[SplitPane, int, float]] | None = None
        self._drag_bounds: tuple[SplitPane, Size, Size] | None = None
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
        self._drag_targets = None
        self._drag_bounds = None
        self.remove_class("-dragging")
        if self.is_mounted:
            self.release_mouse()

    def _resize_bounds_changed(self) -> bool:
        """Distinguish terminal/container resizing from our own divider changes."""
        if self._drag_bounds is None:
            return False
        root, size, screen_size = self._drag_bounds
        return (
            not self.is_attached
            or not root.is_attached
            or not root.display
            or root.content_size != size
            or self.screen.size != screen_size
        )

    def _resize_to_mouse(self, event: events.MouseEvent) -> None:
        if self._drag_origin is not None:
            if self._resize_bounds_changed():
                self.cancel_drag()
                return
            delta = event.screen_offset - self._drag_origin
            targets = (
                self._drag_targets
                if self._drag_targets is not None
                else [(self.split_pane, self._drag_size, self._drag_position)]
            )
            for split, size, _ in targets:
                distance = delta.x if split.orientation == "horizontal" else delta.y
                split._set_first_size(size + distance)

    def _on_mouse_down(self, event: events.MouseDown) -> None:
        if self.is_disabled:
            return
        if event.button != 1 and not (
            event.button == 3 and self.split_pane._modifier_active(event)
        ):
            return
        event.stop()
        event.prevent_default()
        self.screen.clear_selection()
        self.suppress_click()
        self.screen.set_focus(self, scroll_visible=False)
        self._drag_button = event.button
        self._drag_origin = event.screen_offset
        self._drag_size = self.split_pane.first_size
        self._drag_position = self.split_pane.position
        if event.button == 3:
            targets = []
            axes = set()
            root = self.split_pane
            side = self.split_pane._pane_at(event.screen_offset)
            pane = (
                self.split_pane._first_pane
                if side == "first"
                else self.split_pane._second_pane
            )
            region = pane.region
            edges = {
                "horizontal": "second"
                if event.screen_x < region.x + region.width / 2
                else "first",
                "vertical": "second"
                if event.screen_y < region.y + region.height / 2
                else "first",
            }
            for ancestor in self.split_pane.ancestors_with_self:
                if isinstance(ancestor, SplitPane):
                    root = ancestor
                    if (
                        ancestor.orientation not in axes
                        and not ancestor.is_disabled
                        and ancestor._modifier_active(event)
                        and (
                            side is None
                            and ancestor is self.split_pane
                            or ancestor._pane_at(event.screen_offset)
                            == edges[ancestor.orientation]
                        )
                    ):
                        axes.add(ancestor.orientation)
                        targets.append(
                            (ancestor, ancestor.first_size, ancestor.position)
                        )
            self._drag_targets = targets
            self._drag_bounds = (root, root.content_size, self.screen.size)
        self.add_class("-dragging")
        self.capture_mouse()

    def _on_mouse_move(self, event: events.MouseMove) -> None:
        if self._drag_origin is not None:
            event.stop()
            event.prevent_default()
            self._resize_to_mouse(event)

    def _on_mouse_up(self, event: events.MouseUp) -> None:
        if self._drag_origin is not None and event.button == self._drag_button:
            event.stop()
            event.prevent_default()
            self._resize_to_mouse(event)
            self.cancel_drag()

    def _on_mouse_release(self) -> None:
        if self.app.mouse_captured is not self:
            self.cancel_drag()

    def _on_blur(self) -> None:
        # Mouse-down interception may focus us again before a queued Blur from
        # the content's initial focus is delivered.
        if self.is_attached and self.screen.focused is self:
            return
        self.cancel_drag()
        self.split_pane._cancel_swap(restore_focus=False)

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
            targets = (
                self._drag_targets
                if self._drag_targets is not None
                else [(self.split_pane, self._drag_size, self._drag_position)]
            )
            for split, _, position in targets:
                split.position = position
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
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel_swap", show=False, priority=True),
    ]
    drag_modifier: reactive[DragModifier] = reactive("alt", init=False)
    """Modifier for pane swapping and resizing: alt, ctrl, or shift."""
    swappable: reactive[bool] = reactive(True, init=False)
    """Allow modifier-left-drag to swap pane content."""

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

    class Swapped(Message):
        """Two panes exchanged their live content widgets."""

        def __init__(
            self,
            split_pane: SplitPane,
            other: SplitPane,
            pane: Widget,
            other_pane: Widget,
        ) -> None:
            super().__init__()
            self.split_pane = split_pane
            self.other = other
            self.pane = pane
            self.other_pane = other_pane

        @property
        def control(self) -> SplitPane:
            """The split in which the drag started."""
            return self.split_pane

    def __init__(
        self,
        first: Widget,
        second: Widget,
        *,
        orientation: SplitOrientation = "horizontal",
        position: float = 0.5,
        show_divider: bool = True,
        drag_modifier: DragModifier = "alt",
        swappable: bool = True,
        min_first: int = 1,
        min_second: int = 1,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        """Create a split with two content widgets and an initial split ratio."""
        self._drag_pane: PaneSide | None = None
        self._drag_focus: Widget | None = None
        self._drag_preview: _PaneDragPreview | None = None
        self._drag_origin = Offset()
        self._drag_preview_origin = Offset()
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
        self.drag_modifier = drag_modifier
        self.swappable = swappable
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

    def validate_drag_modifier(self, value: DragModifier) -> DragModifier:
        """Match the configurable modifier used by FloatingWindow."""
        if value not in {"alt", "ctrl", "shift"}:
            raise ValueError("drag_modifier must be 'alt', 'ctrl', or 'shift'")
        return value

    def watch_drag_modifier(self) -> None:
        """End gestures when their modifier changes."""
        self._cancel_resize_gesture()
        self._cancel_swap()

    def watch_swappable(self) -> None:
        """End a pane drag if swapping is disabled."""
        self._cancel_swap()

    def _modifier_active(self, event: events.MouseEvent) -> bool:
        """Check the configured modifier before intercepting content input."""
        return getattr(
            event, "meta" if self.drag_modifier == "alt" else self.drag_modifier
        )

    def _pane_at(self, position: Offset) -> PaneSide | None:
        """Find the content pane under a screen coordinate, excluding the divider."""
        for side, wrapper in (
            ("first", self._first_pane),
            ("second", self._second_pane),
        ):
            if wrapper.region.contains(position.x, position.y):
                return "first" if side == "first" else "second"
        return None

    def _get_mouse_down_target(self, event: events.MouseDown) -> Widget | None:
        """Own modifier gestures before a descendant can consume mouse input."""
        if self.is_disabled or not self._modifier_active(event):
            return None
        if self._pane_at(event.screen_offset) is None:
            return None
        if event.button == 3:
            return self._divider
        if event.button == 1 and self.swappable:
            return self
        return None

    async def _on_mouse_down(self, event: events.MouseDown) -> None:
        """Capture a pane swap without moving or selecting its content."""
        if (
            self.is_disabled
            or not self.swappable
            or event.button != 1
            or not self._modifier_active(event)
        ):
            return
        side = self._pane_at(event.screen_offset)
        if side is None:
            return
        event.stop()
        event.prevent_default()
        self.screen.clear_selection()
        self.suppress_click()
        self._drag_pane = side
        self._drag_focus = self.screen.focused
        self.screen.set_focus(self._divider, scroll_visible=False)
        self.capture_mouse()
        pane = self._first_pane if side == "first" else self._second_pane
        region = pane.region.intersection(self.screen.region)
        strips = self.screen._compositor.render_strips()
        preview = _PaneDragPreview(
            [
                strip.crop(region.x, region.right)
                for strip in strips[region.y : region.bottom]
            ]
        )
        preview.styles.width = region.width
        preview.styles.height = region.height
        preview.styles.offset = region.offset
        self._drag_origin = event.screen_offset
        self._drag_preview_origin = region.offset
        self._drag_preview = preview
        pane.add_class("-drag-source")
        await self.screen.mount(preview)

    def _on_mouse_move(self, event: events.MouseMove) -> None:
        """Consume motion while pane content is captured for a drop."""
        if self._drag_pane is not None:
            event.stop()
            event.prevent_default()
            if self._drag_preview is not None:
                self._drag_preview.styles.offset = (
                    self._drag_preview_origin + event.screen_offset - self._drag_origin
                )

    async def _on_mouse_up(self, event: events.MouseUp) -> None:
        """Exchange content with the innermost eligible split at the drop point."""
        if self._drag_pane is None or event.button != 1:
            return
        event.stop()
        event.prevent_default()
        side = self._drag_pane
        target = next(
            (
                widget
                for widget, _ in self.screen.get_widgets_at(
                    event.screen_x, event.screen_y
                )
                if not isinstance(widget, _PaneDragPreview)
                and self._drag_preview not in widget.ancestors
            ),
            None,
        )
        if target is None:
            self._cancel_swap()
            return
        self._cancel_swap()
        for ancestor in target.ancestors_with_self:
            if isinstance(ancestor, SplitPane):
                other_side = ancestor._pane_at(event.screen_offset)
                if other_side is not None:
                    await self._swap_panes(side, ancestor, other_side)
                    break

    def _cancel_swap(self, *, restore_focus: bool = True) -> None:
        """Release capture and optionally restore the pre-drag keyboard focus."""
        if self._drag_pane is None:
            return
        focus = self._drag_focus
        pane = self._first_pane if self._drag_pane == "first" else self._second_pane
        pane.remove_class("-drag-source")
        preview = self._drag_preview
        self._drag_preview = None
        if preview is not None:
            preview.display = False
            preview.remove()
        self._drag_pane = self._drag_focus = None
        if self.app.mouse_captured is self:
            self.release_mouse()
        if (
            restore_focus
            and self.is_attached
            and focus is not None
            and focus.is_attached
            and focus.focusable
        ):
            self.screen.set_focus(focus, scroll_visible=False)

    def _on_mouse_release(self) -> None:
        """Cancel if another widget takes over capture."""
        if self.app.mouse_captured is not self:
            self._cancel_swap()

    def _on_hide(self, event: events.Hide) -> None:
        """Release gestures when the split is hidden."""
        self._cancel_resize_gesture()
        self._cancel_swap(restore_focus=False)

    def _on_unmount(self) -> None:
        """Release a pending pane drag during teardown."""
        self._cancel_swap(restore_focus=False)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Reserve Escape only while this split owns a pane drag."""
        if action == "cancel_swap":
            return self._drag_pane is not None
        return super().check_action(action, parameters)

    def action_cancel_swap(self) -> None:
        """Cancel a pane swap without changing the layout."""
        self._cancel_swap()

    async def _swap_panes(
        self, side: PaneSide, other: SplitPane, other_side: PaneSide
    ) -> None:
        """Exchange unrelated live subtrees without restarting their lifecycle."""
        if (
            self.is_disabled
            or other.is_disabled
            or not self.swappable
            or not other.swappable
        ):
            return
        pane = self.first if side == "first" else self.second
        other_pane = other.first if other_side == "first" else other.second
        if (
            pane is other_pane
            or pane in other_pane.ancestors
            or other_pane in pane.ancestors
        ):
            return
        parent, other_parent = pane.parent, other_pane.parent
        if not isinstance(parent, Widget) or not isinstance(other_parent, Widget):
            return
        # Park one widget while exchanging the two slots. This also permits the
        # content widgets to have the same ID, without unmounting either subtree.
        parking = Widget()
        parking.styles.width = parking.styles.height = 0
        parking.styles.min_width = parking.styles.min_height = 0
        parking.styles.position = "absolute"
        with self.app.batch_update():
            await self.screen.mount(parking)
            try:
                if (
                    self._pruning
                    or other._pruning
                    or pane.parent is not parent
                    or other_pane.parent is not other_parent
                ):
                    return
                pane.reparent(parking)
                other_pane.reparent(parent)
                pane.reparent(other_parent)
                setattr(self, side, other_pane)
                setattr(other, other_side, pane)
            finally:
                await parking.remove()
        self.post_message(self.Swapped(self, other, pane, other_pane))

    def _cancel_resize_gesture(self) -> None:
        """Cancel resizing owned by this split or one of its descendants."""
        if self.is_attached:
            captured = self.app.mouse_captured
            if isinstance(captured, _SplitPaneDivider) and (
                captured.split_pane is self or self in captured.split_pane.ancestors
            ):
                captured.cancel_drag()
        self._divider.cancel_drag()

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
        self._cancel_resize_gesture()
        self._cancel_swap()
        vertical = self.orientation == "vertical"
        self.set_class(vertical, "-vertical")
        self._divider.set_class(vertical, "-vertical")
        self._divider.refresh()
        self._update_sizes()

    def watch_show_divider(self) -> None:
        self._cancel_resize_gesture()
        self._cancel_swap()
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
            self._cancel_resize_gesture()
            self._cancel_swap(restore_focus=False)

    def _on_mount(self) -> None:
        self._update_sizes()

    def _on_resize(self) -> None:
        size = self.content_size
        captured = self.app.mouse_captured
        if (
            isinstance(captured, _SplitPaneDivider)
            and captured._resize_bounds_changed()
        ):
            captured.cancel_drag()
        if size != self._last_content_size:
            # A modifier gesture can resize an ancestor on the other axis.
            # Keep that capture alive while the nested content gets its new size.
            if self._divider._drag_targets is None:
                self._divider.cancel_drag()
            self._cancel_swap()
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
