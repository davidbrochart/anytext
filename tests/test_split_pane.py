"""Interactive pane layout, capture, constraints and resize persistence."""

import anyio
import pytest

from anytext.app import App, ComposeResult
from anytext.geometry import Size
from anytext.pilot import Pilot
from anytext.widgets import Button, SplitPane, Static


class SplitApp(App):
    def __init__(self, orientation="horizontal", **options):
        self.split = SplitPane(
            Static("first"), Static("second"), orientation=orientation, **options
        )
        self.changes = []
        super().__init__()

    def compose(self) -> ComposeResult:
        yield self.split

    def on_split_pane_changed(self, event):
        self.changes.append(event)


async def wait_for_split_layout(pilot: Pilot, split: SplitPane, size: Size) -> None:
    """Wait for both the resize message and the resulting child layout."""
    dimension = "width" if split.orientation == "horizontal" else "height"
    available = getattr(size, dimension) - int(split.show_divider)
    with anyio.fail_after(5):
        while True:
            await pilot.pause()
            if (
                split.content_size == size
                and split.first_size + split.second_size == available
                and getattr(split.first.parent.size, dimension) == split.first_size
                and getattr(split.second.parent.size, dimension) == split.second_size
            ):
                return
            await anyio.sleep(0.01)


@pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
async def test_drag_and_capture(orientation):
    app = SplitApp(orientation)
    async with app.run_test(size=(81, 25)) as pilot:
        await pilot.pause()
        split = app.split
        initial = split.first_size
        region = split.divider.region
        start = region.offset
        finish = (
            (start.x + 7, start.y)
            if orientation == "horizontal"
            else (start.x, start.y + 4)
        )
        delta = 7 if orientation == "horizontal" else 4
        await pilot.mouse_down(offset=start)
        assert app.mouse_captured is split.divider
        await pilot.hover(offset=finish)
        assert split.first_size == initial + delta
        await pilot.mouse_up(offset=finish)
        assert app.mouse_captured is None
        assert split.first_size + split.second_size == (
            80 if orientation == "horizontal" else 24
        )
        assert app.changes[-1].first_size == split.first_size
        assert app.changes[-1].control is split
        first_dimension = (
            split.first.parent.size.width
            if orientation == "horizontal"
            else split.first.parent.size.height
        )
        assert first_dimension == split.first_size


@pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
async def test_minima_and_outside_release(orientation):
    app = SplitApp(orientation, min_first=4, min_second=5)
    async with app.run_test(size=(81, 25)) as pilot:
        await pilot.pause()
        split = app.split
        await pilot.mouse_down(split.divider)
        await pilot.hover(offset=(0, 0))
        assert split.first_size == 4
        await pilot.hover(offset=(80, 24))
        assert split.second_size == 5
        await pilot.mouse_up(offset=(80, 24))
        assert app.mouse_captured is None


@pytest.mark.parametrize(
    "orientation, key", [("horizontal", "right"), ("vertical", "down")]
)
async def test_keyboard_and_reset(orientation, key):
    app = SplitApp(orientation, position=0.25, min_first=3, min_second=4)
    async with app.run_test(size=(81, 25)) as pilot:
        await pilot.pause()
        split = app.split
        split.divider.focus()
        initial = split.first_size
        await pilot.press(key)
        assert split.first_size == initial + 1
        await pilot.press("home")
        assert split.first_size == 3
        await pilot.press("end")
        assert split.second_size == 4
        await pilot.press("enter")
        assert split.first_size == initial


async def test_parent_resize_preserves_preferred_ratio():
    app = SplitApp(position=0.25, min_first=10, min_second=10)
    async with app.run_test(size=(81, 25)) as pilot:
        await wait_for_split_layout(pilot, app.split, Size(81, 25))
        assert app.split.first_size == 20
        await pilot.resize_terminal(13, 25)
        await wait_for_split_layout(pilot, app.split, Size(13, 25))
        assert (app.split.first_size, app.split.second_size) == (6, 6)
        assert app.split.position == 0.25
        await pilot.resize_terminal(121, 25)
        await wait_for_split_layout(pilot, app.split, Size(121, 25))
        assert (app.split.first_size, app.split.second_size) == (30, 90)


async def test_nested_splits_resize_independently():
    inner = SplitPane(Static("top"), Static("bottom"), orientation="vertical")
    outer = SplitPane(Static("left"), inner)
    app = App()
    async with app.run_test(size=(81, 25)) as pilot:
        await app.mount(outer)
        await pilot.pause()
        assert (outer.first_size, inner.first_size) == (40, 12)
        await pilot.mouse_down(inner.divider)
        await pilot.hover(offset=(inner.divider.region.x, inner.divider.region.y + 3))
        await pilot.mouse_up(offset=(inner.divider.region.x, inner.divider.region.y))
        assert inner.first_size == 15
        assert outer.first_size == 40
        outer.position = 0.25
        await pilot.pause()
        assert outer.first_size == 20
        assert inner.size.width == 60
        assert inner.first_size == 15


async def test_capture_cleanup_on_disable_remove_and_cancel():
    app = SplitApp()
    async with app.run_test(size=(81, 25)) as pilot:
        await pilot.pause()
        split = app.split
        await pilot.mouse_down(split.divider)
        await pilot.hover(offset=(split.divider.region.x + 5, 0))
        assert split.first_size == 45
        await pilot.press("escape")
        assert split.first_size == 40
        assert app.mouse_captured is None
        await pilot.mouse_down(split.divider)
        split.disabled = True
        await pilot.pause()
        assert app.mouse_captured is None
        split.disabled = False
        await pilot.mouse_down(split.divider)
        await split.remove()
        assert app.mouse_captured is None


async def test_content_buttons_do_not_start_drag():
    button = Button("Click")
    split = SplitPane(button, Static("second"))
    app = App()
    async with app.run_test(size=(81, 25)) as pilot:
        await app.mount(split)
        await pilot.pause()
        assert await pilot.click(button)
        assert app.mouse_captured is None
        assert split.position == 0.5


async def test_orientation_and_dynamic_minima():
    app = SplitApp()
    async with app.run_test(size=(81, 25)) as pilot:
        await pilot.pause()
        split = app.split
        split.orientation = "vertical"
        await pilot.pause()
        assert split.first.parent.size == (81, 12)
        assert split.divider.size == (81, 1)
        split.min_first = 18
        await pilot.pause()
        assert (split.first_size, split.second_size) == (18, 6)
        split.min_second = 18
        await pilot.pause()
        assert (split.first_size, split.second_size) == (12, 12)


@pytest.mark.parametrize(
    "options",
    [
        {"position": -0.1},
        {"position": 1.1},
        {"position": float("nan")},
        {"orientation": "diagonal"},
        {"min_first": -1},
        {"min_second": -1},
    ],
)
def test_invalid_configuration(options):
    with pytest.raises(ValueError):
        SplitPane(Static(), Static(), **options)


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_backend_independence(backend):
    async def check():
        app = SplitApp()
        async with app.run_test(size=(81, 25)) as pilot:
            await pilot.pause()
            app.split.divider.focus()
            await pilot.press("right")
            assert app.split.first_size == 41

    anyio.run(check, backend=backend)


async def test_resize_during_drag_releases_capture():
    app = SplitApp()
    async with app.run_test(size=(81, 25)) as pilot:
        await pilot.pause()
        await pilot.mouse_down(app.split.divider)
        assert app.mouse_captured is app.split.divider
        await pilot.resize_terminal(81, 30)
        assert app.mouse_captured is None
        assert app.split.first_size == 40


async def test_clicking_constrained_divider_preserves_preferred_ratio():
    app = SplitApp(position=0.25, min_first=10, min_second=10)
    async with app.run_test(size=(13, 25)) as pilot:
        await pilot.pause()
        assert app.split.first_size == 6
        await pilot.click(app.split.divider)
        assert app.split.position == 0.25
        await pilot.resize_terminal(81, 25)
        assert app.split.first_size == 20


@pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
async def test_hidden_divider_uses_no_space_and_still_drags(orientation):
    app = SplitApp(orientation, show_divider=False)
    async with app.run_test(size=(81, 25)) as pilot:
        await pilot.pause()
        split = app.split
        total = 81 if orientation == "horizontal" else 25
        assert split.first_size + split.second_size == total
        first = split.first.parent.region
        second = split.second.parent.region
        if orientation == "horizontal":
            assert first.right == second.x
            assert split.divider.region.x == first.right - 1
        else:
            assert first.bottom == second.y
            assert split.divider.region.y == first.bottom - 1
        before = split.first_size
        start = split.divider.region.offset
        end = (
            (start.x + 3, start.y)
            if orientation == "horizontal"
            else (start.x, start.y + 3)
        )
        assert app.get_widget_at(*start)[0] is split.divider
        await pilot.mouse_down(offset=start)
        await pilot.hover(offset=end)
        await pilot.mouse_up(offset=end)
        assert split.first_size == before + 3
        assert split.first_size + split.second_size == total
        assert app.mouse_captured is None


async def test_hidden_divider_does_not_erase_pane_content():
    split = SplitPane(Static("L" * 40), Static("R" * 40), show_divider=False)
    app = App()
    async with app.run_test(size=(21, 5)) as pilot:
        await app.mount(split)
        await wait_for_split_layout(pilot, split, Size(21, 5))
        expected = "L" * split.first_size + "R" * split.second_size
        assert app.screen._compositor.render_strips(Size(21, 5))[0].text == expected
        split.divider.focus()
        await pilot.hover(split.divider)
        assert app.screen._compositor.render_strips(Size(21, 5))[0].text == expected
        await pilot.press("right")
        await wait_for_split_layout(pilot, split, Size(21, 5))
        assert split.first_size == 11
        expected = "L" * split.first_size + "R" * split.second_size
        assert app.screen._compositor.render_strips(Size(21, 5))[0].text == expected


async def test_toggle_divider_visibility_and_orientation():
    app = SplitApp()
    async with app.run_test(size=(81, 25)) as pilot:
        await pilot.pause()
        split = app.split
        await pilot.mouse_down(split.divider)
        split.show_divider = False
        await pilot.pause()
        assert app.mouse_captured is None
        assert split.first_size + split.second_size == 81
        split.orientation = "vertical"
        await pilot.pause()
        assert split.first_size + split.second_size == 25
        assert split.second.parent.region.y == split.first.parent.region.bottom
        split.show_divider = True
        await pilot.pause()
        assert split.first_size + split.second_size == 24
        assert split.divider.region.y == split.first.parent.region.bottom
        assert split.second.parent.region.y == split.divider.region.bottom


@pytest.mark.parametrize("position", [0, 1])
async def test_hidden_divider_with_collapsed_pane(position):
    app = SplitApp(position=position, min_first=0, min_second=0, show_divider=False)
    async with app.run_test(size=(21, 5)) as pilot:
        await pilot.pause()
        split = app.split
        assert split.first_size + split.second_size == 21
        assert split.divider.region.x in (0, 20)
        assert app.get_widget_at(*split.divider.region.offset)[0] is split.divider
        split.divider.focus()
        await pilot.press("right" if position == 0 else "left")
        assert (split.first_size, split.second_size) == (
            (1, 20) if position == 0 else (20, 1)
        )


async def test_hidden_divider_preserves_wide_character_at_boundary():
    from anytext.geometry import Size

    split = SplitPane(Static("L" * 8 + "🐍"), Static("R" * 11), show_divider=False)
    app = App()
    async with app.run_test(size=(21, 5)) as pilot:
        await app.mount(split)
        await pilot.pause()
        assert split.first_size == 10
        assert (
            app.screen._compositor.render_strips(Size(21, 5))[0].text
            == "L" * 8 + "🐍" + "R" * 11
        )


@pytest.mark.parametrize("show_divider", [True, False])
async def test_demo_horizontal_drag_preserves_both_box_borders(show_divider):
    from anytext.demo.widgets import SplitPanes

    app = App()
    async with app.run_test(size=(81, 40)) as pilot:
        await app.mount(SplitPanes())
        await pilot.pause()
        outer = app.query_one("#split-demo", SplitPane)
        split = outer.second
        split.show_divider = show_divider
        await pilot.pause()
        for end_y in (0, 39, 0, 39):
            divider = split.divider.region
            start = (divider.x + divider.width // 2, divider.y + divider.height // 2)
            await pilot.mouse_down(offset=start)
            await pilot.hover(offset=(start[0], end_y))
            await pilot.mouse_up(offset=(start[0], end_y))
            await pilot.pause()
            strips = app.screen._compositor.render_strips(app.size)
            for pane in (split.first, split.second):
                region = pane.region
                assert region in pane.parent.region, (region, pane.parent.region)
                assert (
                    strips[region.y].text[region.x : region.right]
                    == "╭" + "─" * (region.width - 2) + "╮"
                )
                assert (
                    strips[region.bottom - 1].text[region.x : region.right]
                    == "╰" + "─" * (region.width - 2) + "╯"
                )
