"""A completed scroll must not leave descendants permanently 'scrolling'."""

import anyio
import pytest

from anytext.app import App
from anytext.containers import VerticalScroll
from anytext.demo.widgets import Sparklines
from anytext.widgets import Static


class ScrollingApp(App):
    CSS = """
    #viewport { overflow: auto auto; }
    #before { height: 10; }
    #after { height: 50; }
    Sparklines { width: 120; }
    """

    def compose(self):
        with VerticalScroll(id="viewport"):
            yield Static("Before", id="before")
            yield Sparklines()
            yield Static("After", id="after")


@pytest.mark.parametrize("position", [5.25, 6.75, 10_000.5, -1.25])
async def test_fractional_scroll_finishes_at_its_validated_target(position):
    app = ScrollingApp()
    async with app.run_test(size=(80, 25)) as pilot:
        await pilot.pause(0.05)
        viewport = app.query_one("#viewport", VerticalScroll)
        assert viewport.max_scroll_x > 0
        assert viewport.max_scroll_y > 0
        viewport.scroll_to(x=position, y=position, animate=False, immediate=True)
        assert viewport.scroll_x == viewport.scroll_target_x
        assert viewport.scroll_y == viewport.scroll_target_y


async def test_sparklines_keep_updating_after_fractional_scroll():
    app = ScrollingApp()
    async with app.run_test(size=(80, 25)) as pilot:
        await pilot.pause(0.05)
        viewport = app.query_one("#viewport", VerticalScroll)
        sparks = app.query_one(Sparklines)
        for position in (10.25, 11.75):
            viewport.scroll_to(x=5.25, y=position, animate=False, immediate=True)
            count = sparks.count
            # No mouse/keyboard input or forced refreshes while waiting.
            with anyio.move_on_after(2):
                while sparks.count < count + 2:
                    await anyio.sleep(0.02)
            assert sparks.count >= count + 2
