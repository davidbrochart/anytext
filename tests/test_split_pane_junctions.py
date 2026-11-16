"""Nested divider rules join and repaint when neighboring rules change."""

import pytest

from anytext.app import App
from anytext.containers import Vertical
from anytext.widgets import SplitPane, Static


class JunctionApp(App):
    """Place perpendicular splits on either side of an outer divider."""

    def __init__(self, orientation="vertical", side="second", grid=False):
        super().__init__()
        self.orientation = orientation
        self.side = side
        self.grid = grid

    def compose(self):
        """Build labels around the shared rules without extra borders."""
        opposite = "horizontal" if self.orientation == "vertical" else "vertical"
        self.inner = SplitPane(Static("A"), Static("B"), orientation=opposite)
        first = self.inner if self.side == "first" else Static("First")
        second = self.inner if self.side == "second" else Static("Second")
        if self.grid:
            self.other = SplitPane(Static("C"), Static("D"), orientation=opposite)
            first, second = self.inner, self.other
        self.outer = SplitPane(first, second, orientation=self.orientation)
        yield self.outer


async def settle(pilot):
    """Allow layout messages and coalesced junction repaints to complete."""
    for _ in range(5):
        await pilot.pause()


def glyph(app, split, child):
    """Read the rendered compositor cell shared by two perpendicular rules."""
    vertical = split.orientation == "horizontal"
    x = split.divider.region.x if vertical else child.divider.region.x
    y = child.divider.region.y if vertical else split.divider.region.y
    return app.screen._compositor.render_strips()[y].crop(x, x + 1).text


@pytest.mark.parametrize(
    "orientation,side,expected",
    [
        ("vertical", "second", "┬"),
        ("vertical", "first", "┴"),
        ("horizontal", "second", "├"),
        ("horizontal", "first", "┤"),
    ],
)
async def test_nested_divider_t_junctions(orientation, side, expected):
    """All four T orientations connect without allocating additional cells."""
    app = JunctionApp(orientation, side)
    async with app.run_test(size=(81, 25)) as pilot:
        await settle(pilot)
        assert glyph(app, app.outer, app.inner) == expected
        assert (
            app.outer.divider.size.width
            if orientation == "horizontal"
            else app.outer.divider.size.height
        ) == 1


@pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
async def test_crossing_becomes_two_t_junctions_after_resize(orientation):
    """The parent rule repaints even when only a child's divider moves."""
    app = JunctionApp(orientation, grid=True)
    async with app.run_test(size=(81, 25)) as pilot:
        await settle(pilot)
        assert glyph(app, app.outer, app.inner) == "┼"
        app.inner.position = 0.3
        await settle(pilot)
        assert glyph(app, app.outer, app.inner) == (
            "┤" if orientation == "horizontal" else "┴"
        )
        assert glyph(app, app.outer, app.other) == (
            "├" if orientation == "horizontal" else "┬"
        )


async def test_junction_moves_and_clears_when_child_is_hidden_or_removed():
    """Visibility and teardown cannot leave a cached connector behind."""
    app = JunctionApp()
    async with app.run_test(size=(81, 25)) as pilot:
        await settle(pilot)
        assert glyph(app, app.outer, app.inner) == "┬"
        old_x = app.inner.divider.region.x
        app.inner.position = 0.7
        await settle(pilot)
        strips = app.screen._compositor.render_strips()
        assert strips[app.outer.divider.region.y].crop(old_x, old_x + 1).text == "─"
        assert glyph(app, app.outer, app.inner) == "┬"
        app.inner.show_divider = False
        await settle(pilot)
        assert "┬" not in app.outer.divider.render()
        app.inner.show_divider = True
        await settle(pilot)
        assert glyph(app, app.outer, app.inner) == "┬"
        app.inner.display = False
        await settle(pilot)
        assert "┬" not in app.outer.divider.render()
        app.inner.display = True
        await settle(pilot)
        assert glyph(app, app.outer, app.inner) == "┬"
        await app.inner.remove()
        await settle(pilot)
        assert app.outer.divider.render() == "─" * app.outer.divider.size.width
        assert (
            "┬"
            not in app.screen._compositor.render_strips()[
                app.outer.divider.region.y
            ].text
        )


async def test_padded_nested_split_does_not_join_across_a_gap():
    """A real padding gap must remain separate from an outer rule."""
    app = App()
    async with app.run_test(size=(81, 25)) as pilot:
        inner = SplitPane(Static("A"), Static("B"))
        padded = Vertical(inner)
        padded.styles.padding = 1
        outer = SplitPane(Static("top"), padded, orientation="vertical")
        await app.mount(outer)
        await settle(pilot)
        assert "┬" not in outer.divider.render()
        assert glyph(app, outer, inner) == "─"
