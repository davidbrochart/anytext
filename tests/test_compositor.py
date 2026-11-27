from anytext._compositor import ChopsUpdate
from anytext.app import App, ComposeResult
from anytext.containers import Container
from anytext.geometry import Region
from anytext.strip import Strip
from anytext.widgets import Static


async def test_partial_update_renders_only_the_dirty_row():
    crops: list[Region] = []

    class RecordingStatic(Static):
        def render_lines(self, crop: Region) -> list[Strip]:
            crops.append(crop)
            return super().render_lines(crop)

    class PartialUpdateApp(App):
        def compose(self) -> ComposeResult:
            yield RecordingStatic("\n".join(f"row {y}" for y in range(20)))

    app = PartialUpdateApp()
    async with app.run_test(size=(40, 12)):
        widget = app.query_one(RecordingStatic)
        compositor = app.screen._compositor
        compositor.render_full_update()
        full_chops = compositor._render_chops(compositor.size.region, lambda y: True)
        crops.clear()
        compositor._dirty_regions.add(Region(2, 5, 1, 1))
        update = compositor.render_partial_update()

        assert crops == [Region(0, 5, widget.region.width, 1)]
        assert update is not None
        expected = ChopsUpdate(full_chops, [(5, 2, 3)], update.chop_ends)
        assert update.render_segments(app.console) == expected.render_segments(
            app.console
        )


async def test_compositor_scroll_placements():
    """Regression test for https://github.com/Textualize/textual/issues/5249
    The Static should remain visible.
    """

    class ScrollApp(App):
        CSS = """
        Screen {
            overflow: scroll;
        }
        Container {
            width: 200vw;
        }
        #hello {
            width: 20;
            height: 10;
            offset: 50 10;
            background: blue;
            color: white;
        }
        """

        def compose(self) -> ComposeResult:
            with Container():
                yield Static("Hello", id="hello")

        def on_mount(self) -> None:
            self.screen.scroll_to(20, 0, animate=False)

    app = ScrollApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        static = app.query_one("#hello")
        widgets = app.screen._compositor.visible_widgets
        # The static wasn't scrolled out of view, and should be visible
        # This wasn't the case <= v0.86.1
        assert static in widgets
