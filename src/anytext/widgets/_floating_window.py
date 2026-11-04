"""Floating containers with draggable borders and modifier-drag movement."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import ceil, floor
from typing import ClassVar, Literal

from anytext import events
from anytext.binding import Binding, BindingType
from anytext.geometry import Offset, Region
from anytext.reactive import reactive
from anytext.widget import Widget

MoveModifier = Literal["alt", "ctrl", "shift"]


@dataclass
class _Drag:
    origin: Offset
    button: int
    region: Region
    offset: Offset
    bounds: Region
    edges: tuple[bool, bool, bool, bool]
    rules: dict[str, object]
    changed: bool = False


class FloatingWindow(Widget, can_focus=True):
    """A floating container resized by its border and moved with modifier-drag.

    Drag an edge or corner to resize. Alt-left-drag anywhere to move, or
    Alt-right-drag to resize from the nearest corner, including without borders.
    ``move_modifier`` may instead be ``"ctrl"`` or ``"shift"``. A title is
    optional and uses the existing border, without a separate title bar.
    Geometry and minimum/maximum dimensions are controlled through CSS.
    """

    DEFAULT_CSS = """
    FloatingWindow {
        position: absolute;
        layer: floating-windows;
        layout: vertical;
        offset: 2 1;
        width: 40;
        height: 12;
        min-width: 12;
        min-height: 4;
        border: round $primary;
        background: $surface;
        overflow: hidden hidden;
        &:focus, &:focus-within, &.-dragging { border: round $accent; }
    }
    """
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel_drag", show=False, priority=True),
    ]
    resizable: reactive[bool] = reactive(True, init=False)
    """Whether border dragging or modifier-right-dragging resizes the window."""
    movable: reactive[bool] = reactive(True, init=False)
    """Whether modifier-dragging moves the window."""
    move_modifier: reactive[MoveModifier] = reactive("alt", init=False)
    """Modifier required for moving and resizing: ``alt``, ``ctrl``, or ``shift``."""

    def __init__(
        self,
        *children: Widget,
        title: str | None = None,
        resizable: bool = True,
        movable: bool = True,
        move_modifier: MoveModifier = "alt",
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        self._drag: _Drag | None = None
        super().__init__(
            *children, name=name, id=id, classes=classes, disabled=disabled
        )
        self.border_title = title
        self.resizable = resizable
        self.movable = movable
        self.move_modifier = move_modifier

    def validate_move_modifier(self, value: MoveModifier) -> MoveModifier:
        if value not in {"alt", "ctrl", "shift"}:
            raise ValueError("move_modifier must be 'alt', 'ctrl', or 'shift'")
        return value

    def watch_resizable(self) -> None:
        self._finish_drag()

    def watch_movable(self) -> None:
        self._finish_drag()

    def watch_move_modifier(self) -> None:
        self._finish_drag()

    def watch_disabled(self, disabled: bool) -> None:
        super().watch_disabled(disabled)
        if disabled:
            self._finish_drag()

    def _bounds(self) -> Region:
        return self.parent.scrollable_content_region

    def _edges_at(self, position: Offset) -> tuple[bool, bool, bool, bool]:
        x, y = position - self.region.offset
        border = self.styles.border.spacing
        return (
            bool(border.left and x == 0),
            bool(border.top and y == 0),
            bool(border.right and x == self.region.width - 1),
            bool(border.bottom and y == self.region.height - 1),
        )

    def _modifier_active(self, event: events.MouseEvent) -> bool:
        return getattr(
            event, "meta" if self.move_modifier == "alt" else self.move_modifier
        )

    def _get_mouse_down_target(self, event: events.MouseDown) -> Widget | None:
        if (
            not self.is_disabled
            and self._modifier_active(event)
            and (
                (event.button == 1 and self.movable)
                or (event.button == 3 and self.resizable)
            )
        ):
            return self
        return None

    def _on_mouse_down(self, event: events.MouseDown) -> None:
        if self.is_disabled or event.button not in {1, 3}:
            return
        modifier = self._modifier_active(event)
        resizing = event.button == 3 and modifier and self.resizable
        if event.button == 3 and not resizing:
            return
        # Let an inner floating window own its gestures.
        if event.widget is not None:
            for ancestor in event.widget.ancestors_with_self:
                if ancestor is self:
                    break
                if isinstance(ancestor, FloatingWindow):
                    return
        if self.parent.children[-1] is not self:
            self.parent.move_child(self, after=self.parent.children[-1])
        moving = event.button == 1 and modifier and self.movable
        if moving:
            edges = (False, False, False, False)
        elif resizing:
            x, y = event.screen_offset - self.region.offset
            left = x < self.region.width / 2
            top = y < self.region.height / 2
            edges = (left, top, not left, not top)
        else:
            edges = self._edges_at(event.screen_offset)
        if not moving and (not self.resizable or not any(edges)):
            return
        event.stop()
        event.prevent_default()
        self.focus(scroll_visible=False)
        self.screen.clear_selection()
        bounds = self._bounds()
        self._drag = _Drag(
            event.screen_offset,
            event.button,
            self.region,
            self.styles.offset.resolve(bounds.size, self.screen.size),
            bounds,
            edges,
            {
                name: self.styles.inline.get_rule(name)
                for name in ("width", "height", "offset")
            },
        )
        self.add_class("-dragging")
        self.capture_mouse()

    def _dimension_limits(self) -> tuple[int, int, int, int]:
        gutter = self.styles.gutter
        min_w, max_w, min_h, max_h = self._resolve_extrema(
            self._bounds().size, self.screen.size, Fraction(1), Fraction(1)
        )
        min_width = ceil(max(0, min_w or 0)) + gutter.width
        min_height = ceil(max(0, min_h or 0)) + gutter.height
        max_width = (
            floor(max(0, max_w)) + gutter.width
            if max_w is not None
            else max(min_width, self._bounds().width)
        )
        max_height = (
            floor(max(0, max_h)) + gutter.height
            if max_h is not None
            else max(min_height, self._bounds().height)
        )
        # Like the box model, an explicit CSS maximum wins over a minimum.
        return (
            min(min_width, max_width),
            max_width,
            min(min_height, max_height),
            max_height,
        )

    def _drag_to(self, position: Offset) -> None:
        drag = self._drag
        if drag is None:
            return
        if self._bounds() != drag.bounds:
            self._finish_drag()
            return
        dx, dy = position - drag.origin
        if not (dx or dy or drag.changed):
            return
        left, top, right, bottom = drag.edges
        x, y, width, height = drag.region
        bounds = drag.bounds
        if not any(drag.edges):
            x += dx
            y += dy
        else:
            min_w, max_w, min_h, max_h = self._dimension_limits()
            if left or right:
                available = drag.region.right - bounds.x if left else bounds.right - x
                maximum = max(min_w, min(max_w, available))
                width = max(min_w, min(maximum, width + (-dx if left else dx)))
                if left:
                    x = drag.region.right - width
            if top or bottom:
                available = drag.region.bottom - bounds.y if top else bounds.bottom - y
                maximum = max(min_h, min(max_h, available))
                height = max(min_h, min(maximum, height + (-dy if top else dy)))
                if top:
                    y = drag.region.bottom - height
            # CSS dimensions measure the content when content-box is selected.
            gutter = (
                self.styles.gutter
                if self.styles.box_sizing == "content-box"
                else (0, 0, 0, 0)
            )
            if left or right:
                self.styles.width = width - (gutter[1] + gutter[3])
            if top or bottom:
                self.styles.height = height - (gutter[0] + gutter[2])
        # Leave a small grab area inside the parent, including when shrinking
        # a window that is already mostly outside it.
        visible_width = min(3, width, bounds.width)
        visible_height = min(2, height, bounds.height)
        x = max(bounds.x + visible_width - width, min(bounds.right - visible_width, x))
        y = max(
            bounds.y + visible_height - height, min(bounds.bottom - visible_height, y)
        )
        drag.changed = True
        self.styles.offset = drag.offset + Offset(x - drag.region.x, y - drag.region.y)

    def _on_mouse_move(self, event: events.MouseMove) -> None:
        if self._drag is not None:
            event.stop()
            event.prevent_default()
            self._drag_to(event.screen_offset)
        elif event.widget is self and self.resizable:
            left, top, right, bottom = self._edges_at(event.screen_offset)
            if (left and top) or (right and bottom):
                pointer = "nwse-resize"
            elif (left and bottom) or (right and top):
                pointer = "nesw-resize"
            elif left or right:
                pointer = "ew-resize"
            elif top or bottom:
                pointer = "ns-resize"
            else:
                pointer = "default"
            self.styles.pointer = pointer

    def _on_mouse_up(self, event: events.MouseUp) -> None:
        if self._drag is not None and event.button == self._drag.button:
            event.stop()
            event.prevent_default()
            self._drag_to(event.screen_offset)
            self._finish_drag()

    def _finish_drag(self) -> None:
        self._drag = None
        self.remove_class("-dragging")
        if self.is_mounted and self.app.mouse_captured is self:
            self.release_mouse()

    def _on_mouse_release(self) -> None:
        if self.app.mouse_captured is not self:
            self._finish_drag()

    def _on_blur(self) -> None:
        self._finish_drag()

    def _on_hide(self) -> None:
        self._finish_drag()

    def _on_unmount(self) -> None:
        self._finish_drag()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "cancel_drag":
            return self._drag is not None
        return super().check_action(action, parameters)

    def action_cancel_drag(self) -> None:
        """Restore geometry from before the current drag."""
        if self._drag is not None:
            for name, value in self._drag.rules.items():
                setattr(self.styles, name, value)
            self._finish_drag()
