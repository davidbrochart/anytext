"""Moving mounted subtrees preserves their lifecycle and updates their ancestry."""

import anyio
import pytest

from anytext import events
from anytext._node_list import DuplicateIds
from anytext.app import App, ComposeResult
from anytext.color import Color
from anytext.containers import Horizontal, Vertical
from anytext.css.query import NoMatches
from anytext.message import Message
from anytext.screen import Screen
from anytext.widget import MountError, Widget, WidgetError
from anytext.widgets import Input, SplitPane, Static


class LivePane(Vertical):
    """A stateful subtree with an active worker and timer."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mounts = 0
        self.unmounts = 0
        self.ticks = 0
        self.gate = anyio.Event()

    def compose(self) -> ComposeResult:
        """Include an editable child to check descendant state and focus."""
        yield Input(value="draft", id="editor")

    def on_mount(self) -> None:
        """Start long-lived activity once."""
        self.mounts += 1
        self.job = self.run_worker(self.wait_for_gate())
        self.timer = self.set_interval(0.01, self.tick)

    def on_unmount(self) -> None:
        """Record any unwanted teardown."""
        self.unmounts += 1

    async def wait_for_gate(self) -> str:
        """Remain alive while the pane is moved and its old parent removed."""
        await self.gate.wait()
        return "finished"

    def tick(self) -> None:
        """Count timer callbacks."""
        self.ticks += 1


class ReparentApp(App):
    """Keep source and destination containers on one screen."""

    CSS = """
    #source LivePane { color: red; }
    #destination LivePane { color: blue; }
    #source:focus-within { background: red; }
    #destination:focus-within { background: blue; }
    #source:empty { color: green; }
    """

    def compose(self) -> ComposeResult:
        """Mount a live pane next to an empty destination."""
        with Horizontal():
            yield Vertical(LivePane(id="live"), id="source")
            yield Vertical(id="destination")


async def test_reparent_preserves_lifecycle_focus_workers_and_queries():
    """A moved subtree survives removal of its former parent unchanged."""
    app = ReparentApp()
    async with app.run_test() as pilot:
        pane = app.query_one(LivePane)
        source = app.query_one("#source", Vertical)
        destination = app.query_one("#destination", Vertical)
        editor = pane.query_one(Input)
        app.screen.set_focus(editor)
        await pilot.pause()
        editor.cursor_position = 2
        task, job, timer = pane._task, pane.job, pane.timer
        assert source.query_one("#live") is pane
        assert source.query_one("#editor") is editor
        assert pane.styles.color == Color.parse("red")
        assert pane.reparent(destination) is pane
        assert pane.parent is destination
        assert source.styles.color == Color.parse("green")
        assert app.query_one("#live") is pane
        assert destination.query_one("#editor") is editor
        with pytest.raises(NoMatches):
            source.query_one("#live")
        with pytest.raises(NoMatches):
            source.query_one("#editor")
        await source.remove()
        await pilot.pause()
        assert app.screen.focused is editor and editor.has_focus
        assert editor.value == "draft" and editor.cursor_position == 2
        assert pane._task is task and pane.job is job and pane.timer is timer
        assert pane.mounts == 1 and pane.unmounts == 0
        assert pane.styles.color == Color.parse("blue")
        assert destination.styles.background == Color.parse("blue")
        previous_ticks = pane.ticks
        with anyio.fail_after(3):
            while pane.ticks <= previous_ticks:
                await anyio.sleep(0.01)
        pane.gate.set()
        assert await job.wait() == "finished"


@pytest.mark.parametrize(
    "placement,expected",
    [
        ({}, ["a", "b", "live"]),
        ({"before": 0}, ["live", "a", "b"]),
        ({"after": 0}, ["a", "live", "b"]),
        ({"before": -1}, ["a", "live", "b"]),
        ({"after": -1}, ["a", "b", "live"]),
        ({"before": "#b"}, ["a", "live", "b"]),
        ({"after": "#a"}, ["a", "live", "b"]),
    ],
)
async def test_reparent_insertion_points(placement, expected):
    """Destination insertion points match mount's ordering conventions."""
    app = ReparentApp()
    async with app.run_test():
        destination = app.query_one("#destination", Vertical)
        await destination.mount(Static(id="a"), Static(id="b"))
        app.query_one(LivePane).reparent(destination, **placement)
        assert [child.id for child in destination.children] == expected


async def test_reparent_same_parent_reorders_and_updates_styles():
    """Reordering refreshes positional selectors without restarting widgets."""
    app = App()
    async with app.run_test() as pilot:
        parent = Vertical(Static(id="a"), Static(id="b"), Static(id="c"))
        await app.mount(parent)
        a, b, c = parent.children
        a.styles.width = 10
        a.reparent(parent, after=b)
        assert list(parent.children) == [b, a, c]
        c.reparent(parent, before=b)
        assert list(parent.children) == [c, b, a]
        b.reparent(parent, before=b)
        assert list(parent.children) == [c, b, a]
        c.reparent(parent)
        assert list(parent.children) == [b, a, c]
        await pilot.pause()
        assert a.styles.width.value == 10


async def test_reparent_rejects_invalid_moves_without_mutating_tree():
    """All validation happens before either parent's child list changes."""
    app = ReparentApp()
    async with app.run_test():
        pane = app.query_one(LivePane)
        source = app.query_one("#source", Vertical)
        destination = app.query_one("#destination", Vertical)
        for parent in (pane, pane.query_one(Input)):
            with pytest.raises(WidgetError):
                pane.reparent(parent)
        with pytest.raises(MountError):
            pane.reparent(destination, before=0, after=0)
        with pytest.raises(MountError):
            pane.reparent(destination, before=pane.query_one(Input))
        with pytest.raises(MountError):
            pane.reparent(Vertical())
        with pytest.raises(MountError):
            Static().reparent(destination)
        duplicate = Static(id="live")
        await destination.mount(duplicate)
        with pytest.raises(DuplicateIds):
            pane.reparent(destination)
        assert pane.parent is source
        assert list(source.children) == [pane]
        assert list(destination.children) == [duplicate]
        await destination.remove()
        with pytest.raises(MountError):
            pane.reparent(destination)
        assert pane.parent is source


async def test_reparent_rejects_cross_screen_and_screen_moves():
    """Screen ownership, subscriptions, and app lifetime cannot change."""
    app = ReparentApp()
    async with app.run_test():
        original = app.screen
        pane = app.query_one(LivePane)
        await app.push_screen(Screen())
        with pytest.raises(WidgetError, match="same screen"):
            pane.reparent(app.screen)
        with pytest.raises(WidgetError, match="Screens"):
            original.reparent(app.screen)
        assert pane.screen is original


@pytest.mark.parametrize("attribute", ["disabled", "display", "visible"])
async def test_reparent_resets_ineligible_focus(attribute):
    """A moved input cannot retain focus under hidden or disabled ancestors."""
    app = ReparentApp()
    async with app.run_test() as pilot:
        pane = app.query_one(LivePane)
        destination = app.query_one("#destination", Vertical)
        editor = pane.query_one(Input)
        app.screen.set_focus(editor)
        await pilot.pause()
        setattr(destination, attribute, attribute == "disabled")
        pane.reparent(destination)
        await pilot.pause()
        assert app.screen.focused is not editor
        assert not editor.has_focus


async def test_reparent_updates_message_bubbling_and_focus_ancestry():
    """Messages and descendant-focus notifications follow the new parent."""
    seen = []

    class Ping(Message):
        """A bubbling message emitted by a moved child."""

    class Parent(Vertical):
        """Record messages arriving through this branch."""

        def on_ping(self, event: Ping):
            """Remember the new bubbling route."""
            seen.append((self.id, "ping"))

        def on_descendant_focus(self, event: events.DescendantFocus):
            """Remember the branch gaining a focused child."""
            seen.append((self.id, "focus"))

        def on_descendant_blur(self, event: events.DescendantBlur):
            """Remember the branch losing a focused child."""
            seen.append((self.id, "blur"))

    app = App()
    async with app.run_test() as pilot:
        editor = Input()
        source, destination = Parent(editor, id="old"), Parent(id="new")
        await app.mount(source, destination)
        app.screen.set_focus(editor)
        await pilot.pause()
        seen.clear()
        editor.reparent(destination)
        editor.post_message(Ping())
        await pilot.pause()
        assert ("old", "blur") in seen
        assert ("new", "focus") in seen
        assert ("new", "ping") in seen
        assert ("old", "ping") not in seen
        assert app.screen.focused is editor


async def test_reparent_live_widget_into_split_and_back():
    """Pane layout changes can keep real widgets mounted throughout."""
    app = ReparentApp()
    async with app.run_test(size=(100, 30)) as pilot:
        pane = app.query_one(LivePane)
        source = app.query_one("#source", Vertical)
        left, right = Vertical(), Vertical()
        split = SplitPane(left, right)
        await source.parent.mount(split)
        pane.reparent(left)
        await source.remove()
        await pilot.pause()
        assert pane.region == left.content_region
        pane.reparent(right)
        await pilot.pause()
        assert pane.region == right.content_region
        pane.reparent(split.parent)
        await split.remove()
        await pilot.pause()
        assert pane.is_mounted and pane.mounts == 1 and pane.unmounts == 0


async def test_reparent_updates_parent_key_bindings():
    """The focused child uses its new ancestry's binding namespace."""
    seen = []

    class Parent(Vertical):
        """Bind a key whose action records the current container."""

        BINDINGS = [("f8", "record", "Record")]

        def action_record(self):
            """Record the parent which handled the action."""
            seen.append(self.id)

    app = App()
    async with app.run_test() as pilot:
        editor = Input()
        source, destination = Parent(editor, id="old"), Parent(id="new")
        await app.mount(source, destination)
        app.screen.set_focus(editor)
        await pilot.press("f8")
        editor.reparent(destination)
        await pilot.press("f8")
        assert seen == ["old", "new"]


async def test_reparent_refreshes_positional_selectors():
    """Both old and new siblings get their correct positional styles."""

    class StyledApp(App):
        """Color the first child of each container."""

        CSS = """
        Static { color: blue; }
        Static:first-child { color: red; }
        """

        def compose(self):
            """Mount ordered siblings in source and destination branches."""
            yield Vertical(Static(id="a"), Static(id="b"), id="old")
            yield Vertical(Static(id="c"), id="new")

    app = StyledApp()
    async with app.run_test():
        a, b, c = (app.query_one("#" + name) for name in ("a", "b", "c"))
        a.reparent(app.query_one("#new"), before=c)
        assert a.styles.color == Color.parse("red")
        assert b.styles.color == Color.parse("red")
        assert c.styles.color == Color.parse("blue")
