"""Mouse interaction and geometry constraints for floating windows."""

import anyio
import pytest

from anytext.app import App, ComposeResult
from anytext.geometry import Offset, Region
from anytext.widgets import Button, FloatingWindow, Input, Static, TextArea


class WindowApp(App):
    CSS = """
    FloatingWindow { width: 20; height: 10; offset: 10 5; min-width: 8; min-height: 4; }
    """

    def __init__(self, *children, **options):
        super().__init__()
        self.window = FloatingWindow(*children, **options)
        self.clicks = 0

    def compose(self) -> ComposeResult:
        yield self.window

    def on_button_pressed(self):
        self.clicks += 1


async def wait_for_region(pilot, window, expected):
    await pilot.pause()
    with anyio.move_on_after(5):
        while window.region != expected:
            await pilot.pause()
            await anyio.sleep(0.01)
    assert window.region == expected


@pytest.mark.parametrize(
    "start, delta, expected",
    [
        ((0, 4), (-3, 0), Region(7, 5, 23, 10)),
        ((19, 4), (3, 0), Region(10, 5, 23, 10)),
        ((8, 0), (0, -2), Region(10, 3, 20, 12)),
        ((8, 9), (0, 2), Region(10, 5, 20, 12)),
        ((0, 0), (-3, -2), Region(7, 3, 23, 12)),
        ((19, 0), (3, -2), Region(10, 3, 23, 12)),
        ((0, 9), (-3, 2), Region(7, 5, 23, 12)),
        ((19, 9), (3, 2), Region(10, 5, 23, 12)),
    ],
)
async def test_resize_edges_and_corners(start, delta, expected):
    app = WindowApp(Static("Content"))
    async with app.run_test(size=(80, 30)) as pilot:
        await wait_for_region(pilot, app.window, Region(10, 5, 20, 10))
        origin = Offset(10, 5) + start
        end = origin + delta
        await pilot.mouse_down(offset=origin)
        assert app.mouse_captured is app.window
        await pilot.hover(offset=end)
        await pilot.mouse_up(offset=end)
        await wait_for_region(pilot, app.window, expected)
        assert app.mouse_captured is None


@pytest.mark.parametrize("child", [Static, Input, TextArea, Button])
@pytest.mark.parametrize(
    "modifier, flags",
    [("alt", {"meta": True}), ("ctrl", {"control": True}), ("shift", {"shift": True})],
)
async def test_modifier_drag_moves_over_content(child, modifier, flags):
    app = WindowApp(move_modifier=modifier)
    async with app.run_test(size=(80, 30)) as pilot:
        content = child("Content")
        await app.window.mount(content)
        with anyio.fail_after(5):
            while not content.region.width or not content.region.height:
                await pilot.pause()
                await anyio.sleep(0.01)
        await wait_for_region(pilot, app.window, Region(10, 5, 20, 10))
        await pilot.mouse_down(content, offset=(2, 0), **flags)
        assert app.mouse_captured is app.window
        start = content.region.offset + Offset(2, 0)
        end = start + Offset(4, 3)
        await pilot.hover(offset=end)
        await pilot.mouse_up(offset=end, **flags)
        await wait_for_region(pilot, app.window, Region(14, 8, 20, 10))
        assert app.mouse_captured is None
        assert app.clicks == 0
        assert app.window.border_title is None
        assert app.window.content_size == (18, 8)


@pytest.mark.parametrize(
    "start, end, expected",
    [
        ((10, 9), (79, 9), Region(22, 5, 8, 10)),
        ((18, 5), (18, 29), Region(10, 11, 20, 4)),
        ((29, 9), (79, 9), Region(10, 5, 28, 10)),
        ((18, 14), (18, 29), Region(10, 5, 20, 14)),
    ],
)
async def test_css_minimum_and_maximum(start, end, expected):
    app = WindowApp()
    app.window.styles.max_width = 28
    app.window.styles.max_height = 14
    async with app.run_test(size=(80, 30)) as pilot:
        await wait_for_region(pilot, app.window, Region(10, 5, 20, 10))
        await pilot.mouse_down(offset=start)
        await pilot.hover(offset=end)
        await pilot.mouse_up(offset=end)
        await wait_for_region(pilot, app.window, expected)


async def test_parent_bounds_and_escape_restore_css():
    app = WindowApp()
    async with app.run_test(size=(80, 30)) as pilot:
        await wait_for_region(pilot, app.window, Region(10, 5, 20, 10))
        await pilot.mouse_down(offset=(10, 5))
        await pilot.hover(offset=(0, 0))
        await wait_for_region(pilot, app.window, Region(0, 0, 30, 15))
        await pilot.press("escape")
        await wait_for_region(pilot, app.window, Region(10, 5, 20, 10))
        assert app.mouse_captured is None
        assert not app.window.styles.inline.has_rule("width")
        assert not app.window.styles.inline.has_rule("offset")
        await pilot.mouse_up(offset=(0, 0))
        await pilot.mouse_down(offset=(15, 8), meta=True)
        await pilot.hover(offset=(79, 29))
        await pilot.mouse_up(offset=(79, 29), meta=True)
        await wait_for_region(pilot, app.window, Region(74, 26, 20, 10))


async def test_ordinary_child_click_is_preserved():
    button = Button("Click")
    app = WindowApp(button)
    async with app.run_test(size=(80, 30)) as pilot:
        await wait_for_region(pilot, app.window, Region(10, 5, 20, 10))
        await pilot.click(button)
        assert app.clicks == 1
        assert app.mouse_captured is None
        assert app.window.region == Region(10, 5, 20, 10)


@pytest.mark.parametrize("change", ["disabled", "resizable", "remove", "hide"])
async def test_capture_cleanup(change):
    app = WindowApp()
    async with app.run_test(size=(80, 30)) as pilot:
        await wait_for_region(pilot, app.window, Region(10, 5, 20, 10))
        await pilot.mouse_down(offset=(29, 14))
        assert app.mouse_captured is app.window
        if change == "remove":
            await app.window.remove()
        elif change == "hide":
            app.window.display = False
        else:
            setattr(app.window, change, change == "disabled")
        await pilot.pause()
        assert app.mouse_captured is None


def test_invalid_modifier():
    with pytest.raises(ValueError):
        FloatingWindow(move_modifier="invalid")


async def test_resize_in_padded_parent_and_percentage_limits():
    from anytext.containers import Container

    class NestedApp(App):
        CSS = """
        #desktop { width: 70; height: 25; margin: 1 2; padding: 1 2; border: solid white; }
        FloatingWindow { width: 20; height: 10; offset: 4 3; min-width: 25%; max-width: 50%; }
        """

        def compose(self):
            with Container(id="desktop"):
                yield FloatingWindow(id="window")

    app = NestedApp()
    async with app.run_test(size=(80, 30)) as pilot:
        window = app.query_one(FloatingWindow)
        bounds = app.query_one("#desktop").content_region
        expected = Region(bounds.x + 4, bounds.y + 3, 20, 10)
        await wait_for_region(pilot, window, expected)
        start = (expected.right - 1, expected.y + 3)
        await pilot.mouse_down(offset=start)
        await pilot.hover(offset=(79, start[1]))
        await pilot.mouse_up(offset=(79, start[1]))
        await wait_for_region(pilot, window, expected._replace(width=32))
        assert window.region in bounds


async def test_content_box_and_border_title_take_no_title_bar_row():
    app = WindowApp(title="A title")
    app.window.styles.box_sizing = "content-box"
    async with app.run_test(size=(80, 30)) as pilot:
        await wait_for_region(pilot, app.window, Region(10, 5, 22, 12))
        assert app.window.content_size == (20, 10)
        assert not app.window.children
        await pilot.mouse_down(offset=(31, 16))
        await pilot.hover(offset=(35, 18))
        await pilot.mouse_up(offset=(35, 18))
        await wait_for_region(pilot, app.window, Region(10, 5, 26, 14))
        assert app.window.content_size == (24, 12)


async def test_border_click_preserves_responsive_css():
    app = WindowApp()
    app.window.styles.width = "25%"
    async with app.run_test(size=(80, 30)) as pilot:
        await wait_for_region(pilot, app.window, Region(10, 5, 20, 10))
        original = app.window.styles.inline.get_rules()
        await pilot.click(offset=(29, 14))
        assert app.window.styles.inline.get_rules() == original
        assert app.mouse_captured is None


@pytest.mark.parametrize("option", ["movable", "resizable", "disabled"])
async def test_disabled_gestures(option):
    app = WindowApp(**{option: option == "disabled"})
    async with app.run_test(size=(80, 30)) as pilot:
        await wait_for_region(pilot, app.window, Region(10, 5, 20, 10))
        await pilot.mouse_down(
            offset=(15, 9) if option == "movable" else (29, 14),
            meta=option == "movable",
        )
        assert app.mouse_captured is None


async def test_overlapping_windows_raise_on_click():
    app = WindowApp()
    async with app.run_test(size=(80, 30)) as pilot:
        await wait_for_region(pilot, app.window, Region(10, 5, 20, 10))
        other = FloatingWindow()
        other.styles.offset = (20, 8)
        await app.mount(other)
        await wait_for_region(pilot, other, Region(20, 8, 20, 10))
        assert app.get_widget_at(25, 10)[0] is other
        await pilot.click(offset=(15, 10))
        await pilot.pause()
        assert app.get_widget_at(25, 10)[0] is app.window


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_backend_independence(backend):
    async def check():
        app = WindowApp()
        async with app.run_test(size=(80, 30)) as pilot:
            await wait_for_region(pilot, app.window, Region(10, 5, 20, 10))
            await pilot.mouse_down(offset=(29, 14))
            await pilot.hover(offset=(33, 16))
            await pilot.mouse_up(offset=(33, 16))
            await wait_for_region(pilot, app.window, Region(10, 5, 24, 12))
            assert app.mouse_captured is None
            await pilot.mouse_down(offset=(28, 13), button=3, meta=True)
            await pilot.hover(offset=(31, 14))
            await pilot.mouse_up(offset=(31, 14), button=3, meta=True)
            await wait_for_region(pilot, app.window, Region(10, 5, 27, 13))
            assert app.mouse_captured is None

    anyio.run(check, backend=backend)


async def test_inner_window_owns_modified_drag():
    inner = FloatingWindow(id="inner")
    app = WindowApp(inner)
    app.window.styles.width = 50
    app.window.styles.height = 20
    inner.styles.offset = (2, 1)
    inner.styles.width = 20
    inner.styles.height = 8
    async with app.run_test(size=(80, 30)) as pilot:
        await wait_for_region(pilot, app.window, Region(10, 5, 50, 20))
        await wait_for_region(pilot, inner, Region(13, 7, 20, 8))
        await pilot.mouse_down(offset=(18, 10), meta=True)
        assert app.mouse_captured is inner
        await pilot.hover(offset=(22, 12))
        await pilot.mouse_up(offset=(22, 12))
        await wait_for_region(pilot, inner, Region(17, 9, 20, 8))
        assert app.window.region == Region(10, 5, 50, 20)


async def test_parent_resize_ends_drag_on_next_mouse_event():
    app = WindowApp()
    async with app.run_test(size=(80, 30)) as pilot:
        await wait_for_region(pilot, app.window, Region(10, 5, 20, 10))
        await pilot.mouse_down(offset=(29, 14))
        await pilot.resize_terminal(70, 25)
        with anyio.fail_after(5):
            while app.screen.size != (70, 25):
                await pilot.pause()
                await anyio.sleep(0.01)
        await pilot.hover(offset=(33, 16))
        assert app.mouse_captured is None
        assert app.window.region == Region(10, 5, 20, 10)


async def test_modifier_gesture_precedes_child_mouse_handlers():
    class ConsumesMouse(Static):
        def on_mouse_down(self, event):
            event.stop()
            raise AssertionError("The child must not receive the window's move gesture")

    app = WindowApp(ConsumesMouse("Content"))
    async with app.run_test(size=(80, 30)) as pilot:
        await wait_for_region(pilot, app.window, Region(10, 5, 20, 10))
        await pilot.mouse_down(offset=(14, 6), meta=True)
        assert app.mouse_captured is app.window
        await pilot.hover(offset=(18, 8))
        await pilot.mouse_up(offset=(18, 8))
        await wait_for_region(pilot, app.window, Region(14, 7, 20, 10))


async def test_moving_editor_keeps_selection():
    app = WindowApp()
    async with app.run_test(size=(80, 30)) as pilot:
        editor = TextArea("First line\nSecond line\nThird line")
        await app.window.mount(editor)
        await wait_for_region(pilot, app.window, Region(10, 5, 20, 10))
        selection = editor.selection
        await pilot.mouse_down(offset=(16, 8), meta=True)
        await pilot.hover(offset=(20, 10))
        await pilot.mouse_up(offset=(20, 10))
        await wait_for_region(pilot, app.window, Region(14, 7, 20, 10))
        assert editor.selection == selection


@pytest.mark.parametrize("borderless", [False, True])
@pytest.mark.parametrize(
    "modifier, flags",
    [("alt", {"meta": True}), ("ctrl", {"control": True}), ("shift", {"shift": True})],
)
@pytest.mark.parametrize(
    "left, top", [(True, True), (False, True), (True, False), (False, False)]
)
async def test_modifier_right_drag_resizes_nearest_corner(
    borderless, modifier, flags, left, top
):
    app = WindowApp(move_modifier=modifier)
    if borderless:
        app.window.styles.border = ("none", "white")
    async with app.run_test(size=(80, 30)) as pilot:
        await wait_for_region(pilot, app.window, Region(10, 5, 20, 10))
        editor = TextArea("Content")
        await app.window.mount(editor)
        await pilot.pause()
        selection = editor.selection
        start = Offset(14 if left else 25, 7 if top else 12)
        end = start + Offset(-3 if left else 3, -2 if top else 2)
        await pilot.mouse_down(offset=start, button=3, **flags)
        assert app.mouse_captured is app.window
        # Releasing another button must not end this gesture.
        await pilot.mouse_up(offset=start, button=1, **flags)
        assert app.mouse_captured is app.window
        await pilot.hover(offset=end)
        await pilot.mouse_up(offset=end, button=3, **flags)
        await wait_for_region(
            pilot, app.window, Region(7 if left else 10, 3 if top else 5, 23, 12)
        )
        assert app.mouse_captured is None
        assert editor.selection == selection
        if borderless:
            assert app.window.styles.border.spacing == (0, 0, 0, 0)


@pytest.mark.parametrize("modifier, resizable", [(False, True), (True, False)])
async def test_right_drag_requires_modifier_and_resizable(modifier, resizable):
    app = WindowApp(resizable=resizable)
    async with app.run_test(size=(80, 30)) as pilot:
        await wait_for_region(pilot, app.window, Region(10, 5, 20, 10))
        await pilot.mouse_down(offset=(29, 14), button=3, meta=modifier)
        await pilot.hover(offset=(33, 16))
        await pilot.mouse_up(offset=(33, 16), button=3, meta=modifier)
        assert app.window.region == Region(10, 5, 20, 10)
        assert app.mouse_captured is None


async def test_modifier_resize_limits_and_escape_without_movement_enabled():
    app = WindowApp(movable=False)
    app.window.styles.max_width = 28
    app.window.styles.max_height = 14
    async with app.run_test(size=(80, 30)) as pilot:
        await wait_for_region(pilot, app.window, Region(10, 5, 20, 10))
        await pilot.mouse_down(offset=(25, 12), button=3, meta=True)
        await pilot.hover(offset=(79, 29))
        await wait_for_region(pilot, app.window, Region(10, 5, 28, 14))
        await pilot.hover(offset=(0, 0))
        await wait_for_region(pilot, app.window, Region(10, 5, 8, 4))
        await pilot.press("escape")
        await wait_for_region(pilot, app.window, Region(10, 5, 20, 10))
        assert app.mouse_captured is None


@pytest.mark.parametrize(
    "delta, outside",
    [((-15, 0), (7, 14)), ((15, 0), (54, 14)), ((0, -8), (26, 4)), ((0, 6), (26, 23))],
)
async def test_moving_past_parent_clips_paint_and_mouse_targets(delta, outside):
    content = Static("\n".join(["C" * 30] * 20))
    inner = FloatingWindow(content)
    inner.styles.width = 20
    inner.styles.height = 8
    app = WindowApp(inner)
    app.window.styles.width = 40
    app.window.styles.height = 16
    async with app.run_test(size=(80, 30)) as pilot:
        await wait_for_region(pilot, app.window, Region(10, 5, 40, 16))
        await wait_for_region(pilot, inner, Region(21, 11, 20, 8))
        start = Offset(26, 14)
        end = start + delta
        expected = Region(21 + delta[0], 11 + delta[1], 20, 8)
        await pilot.mouse_down(offset=start, meta=True)
        assert app.mouse_captured is inner
        await pilot.hover(offset=end)
        await wait_for_region(pilot, inner, expected)
        strips = app.screen._compositor.render_strips(app.size)
        outside_widget = app.get_widget_at(*outside)[0]
        assert inner not in outside_widget.ancestors_with_self
        assert strips[outside[1]].text[outside[0]] != "C"
        visible = inner.content_region.intersection(app.window.content_region)
        point = visible.offset
        assert app.get_widget_at(*point)[0] is content
        assert strips[point.y].text[point.x] == "C"
        # Capture keeps working across the parent's boundary, including return.
        await pilot.hover(offset=start)
        await pilot.mouse_up(offset=start, meta=True)
        await wait_for_region(pilot, inner, Region(21, 11, 20, 8))
        assert app.mouse_captured is None
        await pilot.mouse_down(offset=start, meta=True)
        await pilot.hover(offset=end)
        await pilot.mouse_up(offset=end, meta=True)
        await wait_for_region(pilot, inner, expected)
        assert app.mouse_captured is None


@pytest.mark.parametrize("borderless", [False, True])
@pytest.mark.parametrize("end", [(0, 0), (99, 0), (0, 39), (99, 39)])
async def test_window_keeps_a_grab_area_at_parent_corners(borderless, end):
    inner = FloatingWindow()
    inner.styles.offset = (5, 3)
    inner.styles.width = 20
    inner.styles.height = 10
    if borderless:
        inner.styles.border = ("none", "white")
    app = WindowApp(inner)
    app.window.styles.offset = (20, 10)
    app.window.styles.width = 40
    app.window.styles.height = 20
    async with app.run_test(size=(100, 40)) as pilot:
        await wait_for_region(pilot, app.window, Region(20, 10, 40, 20))
        initial = Region(26, 14, 20, 10)
        await wait_for_region(pilot, inner, initial)
        await pilot.mouse_down(offset=(35, 18), meta=True)
        await pilot.hover(offset=end)
        await pilot.mouse_up(offset=end, meta=True)
        assert app.mouse_captured is None
        visible = inner.region.intersection(app.window.content_region)
        assert visible.width >= 3
        assert visible.height >= 2
        assert inner in app.get_widget_at(*visible.offset)[0].ancestors_with_self
        # Change focus, then start a new drag using only the visible patch.
        app.window.focus(scroll_visible=False)
        await pilot.pause()
        start = visible.offset
        return_to = start + (initial.offset - inner.region.offset)
        await pilot.mouse_down(offset=start, meta=True)
        assert app.mouse_captured is inner
        await pilot.hover(offset=return_to)
        await pilot.mouse_up(offset=return_to, meta=True)
        await wait_for_region(pilot, inner, initial)
        assert app.mouse_captured is None


async def test_shrinking_a_clipped_window_keeps_it_reachable():
    inner = FloatingWindow()
    inner.styles.offset = (5, 3)
    inner.styles.width = 20
    inner.styles.height = 10
    app = WindowApp(inner)
    app.window.styles.offset = (20, 10)
    app.window.styles.width = 40
    app.window.styles.height = 20
    async with app.run_test(size=(100, 40)) as pilot:
        await wait_for_region(pilot, app.window, Region(20, 10, 40, 20))
        await wait_for_region(pilot, inner, Region(26, 14, 20, 10))
        await pilot.mouse_down(offset=(35, 18), meta=True)
        await pilot.hover(offset=(0, 18))
        await pilot.mouse_up(offset=(0, 18), meta=True)
        await wait_for_region(pilot, inner, Region(4, 14, 20, 10))
        await pilot.mouse_down(offset=(22, 21), button=3, meta=True)
        await pilot.hover(offset=(0, 0))
        await pilot.mouse_up(offset=(0, 0), button=3, meta=True)
        visible = inner.region.intersection(app.window.content_region)
        assert inner.region.size == (8, 4)
        assert visible.width >= 3
        assert visible.height >= 2
        assert inner in app.get_widget_at(*visible.offset)[0].ancestors_with_self
