from anytext.app import App, ComposeResult
from anytext.containers import Vertical
from anytext.widgets import Footer, Header, Label, Log, OptionList, SplitPane, TextArea


class SplitPanesApp(App):
    TITLE = "Resizable split panes"
    CSS = """
    .pane-title { height: 1; background: $primary; padding: 0 1; }
    #instructions { height: auto; padding: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(
            "Drag a divider. Tab to focus it; arrows resize, Enter resets.",
            id="instructions",
        )
        editor = Vertical(
            Label("Editor", classes="pane-title"),
            TextArea(
                "# Resize this editor by dragging its borders\n\nprint('Hello, Anytext!')\n"
            ),
        )
        output = Vertical(Label("Output", classes="pane-title"), Log())
        yield SplitPane(
            Vertical(
                Label("Files", classes="pane-title"),
                OptionList("app.py", "README.md", "settings.toml"),
            ),
            SplitPane(
                editor,
                output,
                orientation="vertical",
                position=0.7,
                min_first=3,
                min_second=2,
            ),
            position=0.25,
            min_first=12,
            min_second=20,
        )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(Log).write_line("Hello, Anytext!")


if __name__ == "__main__":
    SplitPanesApp().run()
