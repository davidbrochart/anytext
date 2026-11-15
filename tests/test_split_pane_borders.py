"""Direct pane borders, corners and divider junctions resize shared boundaries."""

import pytest

from anytext.app import App
from anytext.containers import Vertical
from anytext.geometry import Offset
from anytext.widgets import Input, SplitPane, Static


class BorderApp(App):
    """A bordered left pane and two bordered panes in the right column."""

    CSS = ".pane { height: 1fr; border: solid white; min-width: 0; min-height: 0; }"

    def __init__(self, show_divider=True, wrapped=False):
        super().__init__()
        self.show_divider = show_divider
        self.wrapped = wrapped

    def compose(self):
        """Build the same nested arrangement as the widget demo."""
        self.top = Static("Top", classes="pane")
        self.bottom = Static("Bottom", classes="pane")
        self.inner = SplitPane(
            Vertical(self.top) if self.wrapped else self.top,
            Vertical(self.bottom) if self.wrapped else self.bottom,
            orientation="vertical",
            show_divider=self.show_divider,
        )
        self.outer = SplitPane(
            Static("Left", classes="pane"), self.inner, show_divider=self.show_divider
        )
        yield self.outer


@pytest.mark.parametrize("wrapped", [True, False])
@pytest.mark.parametrize("show_divider", [True, False])
@pytest.mark.parametrize(
    "edge", ["left", "bottom", "bottom-left", "top-left", "outside"]
)
async def test_border_and_corner_drag(wrapped, show_divider, edge):
    """Edges move their adjacent split; a shared corner moves both axes."""
    app = BorderApp(show_divider, wrapped=wrapped)
    async with app.run_test(size=(81, 25)) as pilot:
        for _ in range(3):
            await pilot.pause()
        outer, inner = app.outer.first_size, app.inner.first_size
        region = app.top.region
        start = {
            "left": region.offset + Offset(0, region.height // 2),
            "bottom": region.offset + Offset(region.width // 2, region.height - 1),
            "bottom-left": region.offset + Offset(0, region.height - 1),
            "top-left": region.offset,
            "outside": region.offset + Offset(region.width - 1, 0),
        }[edge]
        task = app.top._task
        await pilot.mouse_down(offset=start)
        if edge != "outside":
            assert app.mouse_captured is app.inner.divider
        finish = start + (Offset(-3, 2) if edge == "outside" else Offset(3, 2))
        await pilot.hover(offset=finish)
        await pilot.mouse_up(offset=finish)
        await pilot.pause()
        assert app.outer.first_size == outer + (3 if "left" in edge else 0)
        assert app.inner.first_size == inner + (2 if "bottom" in edge else 0)
        assert app.mouse_captured is None
        assert app.top._task is task


async def test_corner_escape_restores_both_splits():
    """Escape restores each divider participating in a border gesture."""
    app = BorderApp()
    async with app.run_test(size=(81, 25)) as pilot:
        for _ in range(3):
            await pilot.pause()
        positions = app.outer.position, app.inner.position
        region = app.top.region
        start = region.offset + Offset(0, region.height - 1)
        await pilot.hover(offset=start)
        assert app.inner._first_pane.styles.pointer == "nesw-resize"
        await pilot.mouse_down(offset=start)
        await pilot.hover(offset=start + Offset(3, 2))
        await pilot.press("escape")
        await pilot.pause()
        assert (app.outer.position, app.inner.position) == positions
        assert app.mouse_captured is None


async def test_divider_junction_moves_both_axes():
    """An inner divider's endpoint also grabs the adjacent enclosing divider."""
    app = BorderApp()
    async with app.run_test(size=(81, 25)) as pilot:
        for _ in range(3):
            await pilot.pause()
        outer, inner = app.outer.first_size, app.inner.first_size
        start = app.inner.divider.region.offset
        await pilot.mouse_down(offset=start)
        await pilot.hover(offset=start + Offset(3, 2))
        await pilot.mouse_up(offset=start + Offset(3, 2))
        await pilot.pause()
        assert app.outer.first_size == outer + 3
        assert app.inner.first_size == inner + 2


async def test_small_input_border_remains_interactive():
    """A child input's border inside a larger pane is not a pane edge."""
    app = App()
    async with app.run_test(size=(81, 25)) as pilot:
        field = Input("editable")
        split = SplitPane(field, Static("other"))
        await app.mount(split)
        for _ in range(3):
            await pilot.pause()
        initial = split.position
        await pilot.mouse_down(field, offset=(0, 1))
        assert app.mouse_captured is not split.divider
        await pilot.mouse_up(field, offset=(0, 1))
        assert split.position == initial
        assert field.has_focus
