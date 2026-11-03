from anytext.app import App, ComposeResult
from anytext.widgets import Button, FloatingWindow, Label, TextArea


class FloatingWindowsApp(App):
    CSS = """
    Screen { layers: background floating-windows; }
    #instructions { layer: background; }
    #editor { width: 44; height: 15; offset: 3 3; }
    #tools { width: 24; height: 8; offset: 40 12; }
    """

    def compose(self) -> ComposeResult:
        yield Label(
            "Drag borders to resize. Alt+left-drag moves; Alt+right-drag resizes. Escape cancels.",
            id="instructions",
        )
        with FloatingWindow(title="Editor", id="editor"):
            yield TextArea(
                "# This window has a border title, but no title bar.\n\nprint('Hello!')\n"
            )
        with FloatingWindow(id="tools"):
            yield Label("This window has no title.")
            yield Button("A normal button")


if __name__ == "__main__":
    FloatingWindowsApp().run()
