"""Modifier gestures work over interactive content without remounting it."""

import pytest

from anytext.app import App
from anytext.geometry import Offset
from anytext.widgets import Button, Input, SplitPane, TextArea


class GestureApp(App):
    """Track pane swaps and accidental content clicks."""

    def __init__(self, child=Input, **options):
        super().__init__()
        self.child_type = child
        self.options = options
        self.swaps = []
        self.clicks = 0

    def compose(self):
        """Mount the split under test."""
        self.first = self.child_type("first", id="same")
        self.second = self.child_type("second", id="same")
        self.split = SplitPane(self.first, self.second, **self.options)
        yield self.split

    def on_split_pane_swapped(self, event):
        """Record the public swap notification."""
        self.swaps.append(event)

    def on_button_pressed(self):
        """Catch clicks which escaped the modifier gesture."""
        self.clicks += 1


@pytest.mark.parametrize("child", [Button, Input, TextArea])
@pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
@pytest.mark.parametrize("show_divider", [True, False])
async def test_modifier_right_drag_resizes_over_content(
    child, orientation, show_divider
):
    """The containing divider captures right-drag from either kind of pane."""
    app = GestureApp(child, orientation=orientation, show_divider=show_divider)
    async with app.run_test(size=(81, 25)) as pilot:
        await pilot.pause()
        split = app.split
        initial = split.first_size
        start = app.second.region.offset + Offset(2, 1)
        finish = start + (Offset(4, 0) if orientation == "horizontal" else Offset(0, 3))
        await pilot.mouse_down(offset=start, meta=True, button=3)
        assert app.mouse_captured is split.divider
        await pilot.hover(offset=finish)
        await pilot.mouse_up(offset=finish, meta=True, button=3)
        await pilot.pause()
        assert split.first_size == initial + (4 if orientation == "horizontal" else 3)
        assert app.mouse_captured is None
        assert app.clicks == 0 and not app.swaps


@pytest.mark.parametrize("child", [Button, Input, TextArea])
@pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
@pytest.mark.parametrize("show_divider", [True, False])
async def test_modifier_left_drag_swaps_live_widgets(child, orientation, show_divider):
    """Content widgets with equal IDs keep their tasks and text when exchanged."""
    app = GestureApp(child, orientation=orientation, show_divider=show_divider)
    async with app.run_test(size=(81, 25)) as pilot:
        await pilot.pause()
        source, target = app.first, app.second
        source_task, target_task = source._task, target._task
        finish = target.region.offset + Offset(2, 1)
        await pilot.mouse_down(source, offset=(2, 1), meta=True)
        assert app.mouse_captured is app.split
        await pilot.hover(offset=finish)
        await pilot.mouse_up(offset=finish, meta=True)
        await pilot.pause()
        assert app.split.first is target and app.split.second is source
        assert source._task is source_task and target._task is target_task
        assert source.is_mounted and target.is_mounted
        assert app.split.position == 0.5
        if orientation == "horizontal":
            assert target.region.right <= source.region.x
        else:
            assert target.region.bottom <= source.region.y
        assert app.swaps[-1].pane is source
        assert app.swaps[-1].other_pane is target
        assert app.mouse_captured is None and app.clicks == 0


async def test_swap_across_nested_splits_keeps_focus_and_ratios():
    """Leaf content can move between splits without changing their geometry."""
    app = App()
    async with app.run_test(size=(100, 30)) as pilot:
        left, top, bottom = Input("left"), Input("top"), Input("bottom")
        inner = SplitPane(top, bottom, orientation="vertical", position=0.3)
        outer = SplitPane(left, inner, position=0.4)
        await app.mount(outer)
        await pilot.pause()
        finish = bottom.region.offset + Offset(2, 1)
        await pilot.mouse_down(left, offset=(2, 1), meta=True)
        await pilot.hover(offset=finish)
        await pilot.mouse_up(offset=finish, meta=True)
        await pilot.pause()
        assert outer.first is bottom and outer.second is inner
        assert inner.first is top and inner.second is left
        assert outer.position == 0.4 and inner.position == 0.3
        assert app.screen.focused is left


async def test_nested_modifier_resize_adjusts_each_axis():
    """Nested content resizes the nearest split on each axis."""
    app = App()
    async with app.run_test(size=(100, 30)) as pilot:
        inner = SplitPane(Input("top"), Input("bottom"), orientation="vertical")
        outer = SplitPane(Input("left"), inner)
        await app.mount(outer)
        for _ in range(3):
            await pilot.pause()
        initial = inner.first_size
        outer_initial = outer.first_size
        start = inner.first.region.offset + Offset(
            2, inner.first.parent.region.height - 2
        )
        finish = start + Offset(-5, 3)
        await pilot.mouse_down(offset=start, meta=True, button=3)
        assert app.mouse_captured is inner.divider
        await pilot.hover(offset=finish)
        await pilot.pause()
        assert app.mouse_captured is inner.divider
        assert outer.first_size == outer_initial - 5
        assert inner.first_size == initial + 3
        await pilot.hover(offset=start)
        await pilot.pause()
        assert outer.first_size == outer_initial
        assert inner.first_size == initial
        await pilot.hover(offset=finish)
        await pilot.press("escape")
        await pilot.pause()
        assert app.mouse_captured is None
        assert outer.first_size == outer_initial
        assert inner.first_size == initial


@pytest.mark.parametrize(
    "change",
    [
        "escape",
        "disabled",
        "hidden",
        "remove",
        "orientation",
        "show_divider",
        "swappable",
    ],
)
async def test_swap_capture_cleanup(change):
    """Interrupted gestures release capture and leave content in place."""
    app = GestureApp()
    async with app.run_test(size=(81, 25)) as pilot:
        await pilot.mouse_down(app.first, offset=(2, 1), meta=True)
        assert app.mouse_captured is app.split
        if change == "escape":
            await pilot.press("escape")
        elif change == "remove":
            await app.split.remove()
        elif change == "hidden":
            app.split.display = False
        elif change == "orientation":
            app.split.orientation = "vertical"
        elif change == "show_divider":
            app.split.show_divider = False
        elif change == "swappable":
            app.split.swappable = False
        else:
            app.split.disabled = True
        await pilot.pause()
        if change == "hidden":
            # The refresh at the end of pause posts Hide; drain that message
            # before checking the cleanup performed by the Hide handler.
            await pilot.pause()
        assert app.mouse_captured is None
        assert app.split._drag_preview is None
        assert app.split.first is app.first and app.split.second is app.second
        assert not app.swaps


@pytest.mark.parametrize(
    "modifier,flags", [("ctrl", {"control": True}), ("shift", {"shift": True})]
)
async def test_configurable_modifier(modifier, flags):
    """Applications may avoid desktop Alt-mouse bindings."""
    app = GestureApp(drag_modifier=modifier)
    async with app.run_test(size=(81, 25)) as pilot:
        finish = app.second.region.offset + Offset(2, 1)
        await pilot.mouse_down(app.first, offset=(2, 1), **flags)
        assert app.mouse_captured is app.split
        await pilot.mouse_up(offset=finish, **flags)
        await pilot.pause()
        assert app.split.first is app.second


async def test_ordinary_clicks_and_disabled_swapping_are_preserved():
    """Unmodified clicks and opted-out modifier clicks still reach content."""
    app = GestureApp(Button, swappable=False)
    async with app.run_test(size=(81, 25)) as pilot:
        app.first.active_effect_duration = 0
        await pilot.click(app.first)
        await pilot.click(app.first, meta=True)
        assert app.clicks == 2
        assert app.mouse_captured is None and not app.swaps


def test_invalid_drag_modifier():
    """Reject unsupported modifier names before mounting."""
    with pytest.raises(ValueError, match="drag_modifier"):
        SplitPane(Input(), Input(), drag_modifier="invalid")


@pytest.mark.parametrize("button", [1, 3])
async def test_focused_divider_can_start_modifier_drag_over_editor(button):
    """A queued blur cannot cancel a divider which already regained focus."""
    app = GestureApp(TextArea)
    async with app.run_test(size=(81, 25)) as pilot:
        app.screen.set_focus(app.split.divider)
        await pilot.pause()
        await pilot.mouse_down(app.first, offset=(2, 1), meta=True, button=button)
        assert app.mouse_captured is (app.split if button == 1 else app.split.divider)
        await pilot.press("escape")
        assert app.mouse_captured is None


@pytest.mark.parametrize("cancel", [True, False])
async def test_floating_preview_follows_pointer_and_cleans_up(cancel):
    """A pane snapshot follows the pointer without moving its live session."""
    app = GestureApp()
    async with app.run_test(size=(81, 25)) as pilot:
        await pilot.pause()
        source = app.first
        parent, task = source.parent, source._task
        start = source.region.offset + Offset(2, 1)
        finish = app.second.region.offset + Offset(2, 1)
        await pilot.mouse_down(offset=start, meta=True)
        await pilot.pause()
        preview = app.split._drag_preview
        assert preview is not None and preview.is_mounted
        origin = preview.region.offset
        assert any("first" in strip.text for strip in preview._strips)
        await pilot.hover(offset=finish)
        await pilot.pause()
        assert preview.region.offset == origin + finish - start
        assert source.parent is parent and source._task is task
        if cancel:
            await pilot.press("escape")
        else:
            await pilot.mouse_up(offset=finish, meta=True)
        await pilot.pause()
        assert app.split._drag_preview is None
        assert not preview.is_attached
        assert source._task is task
        assert app.split.first is (source if cancel else app.second)


@pytest.mark.parametrize("show_divider", [True, False])
@pytest.mark.parametrize(
    "corner", ["top-left", "top-right", "bottom-left", "bottom-right"]
)
async def test_modifier_resize_uses_grabbed_corner(corner, show_divider):
    """A middle pane chooses the correct boundary among same-axis ancestors."""
    app = App()
    async with app.run_test(size=(100, 40)) as pilot:
        middle = Input("middle")
        bottom_split = SplitPane(
            middle, Input("bottom"), orientation="vertical", show_divider=show_divider
        )
        rows = SplitPane(
            Input("top"),
            bottom_split,
            orientation="vertical",
            show_divider=show_divider,
        )
        right_split = SplitPane(rows, Input("right"), show_divider=show_divider)
        columns = SplitPane(Input("left"), right_split, show_divider=show_divider)
        await app.mount(columns)
        splits = [columns, right_split, rows, bottom_split]
        # Let resize events settle through every level before measuring.
        for _ in splits:
            await pilot.pause()
        assert all(split._available == split._available_space() for split in splits)
        sizes = [split.first_size for split in splits]
        positions = [split.position for split in splits]
        region = middle.parent.region
        left = corner.endswith("left")
        top = corner.startswith("top")
        start = region.offset + Offset(
            1 if left else region.width - 2, 1 if top else region.height - 2
        )
        await pilot.mouse_down(offset=start, meta=True, button=3)
        expected_targets = {
            columns if left else right_split,
            rows if top else bottom_split,
        }
        assert {
            target[0] for target in bottom_split.divider._drag_targets
        } == expected_targets
        await pilot.hover(offset=start + Offset(2, 1))
        await pilot.pause()
        assert app.mouse_captured is bottom_split.divider
        await pilot.mouse_up(offset=start + Offset(2, 1), meta=True, button=3)
        await pilot.pause()
        assert columns.first_size == sizes[0] + (2 if left else 0)
        if left:
            assert right_split.position == positions[1]
        else:
            assert right_split.first_size == sizes[1] + 2
        assert rows.first_size == sizes[2] + (1 if top else 0)
        if top:
            assert bottom_split.position == positions[3]
        else:
            assert bottom_split.first_size == sizes[3] + 1


async def test_modifier_resize_at_outside_corner_keeps_opposite_edges_fixed():
    """An outside corner never falls back to the opposite internal divider."""
    app = GestureApp()
    async with app.run_test(size=(81, 25)) as pilot:
        await pilot.pause()
        initial = app.split.first_size
        await pilot.mouse_down(app.first, offset=(1, 1), meta=True, button=3)
        await pilot.hover(offset=(5, 3))
        await pilot.mouse_up(offset=(5, 3), meta=True, button=3)
        await pilot.pause()
        assert app.split.first_size == initial
