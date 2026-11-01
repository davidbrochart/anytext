from anytext.app import App, ComposeResult
from anytext.widgets import Footer


class NewPaletteBindingApp(App):
    COMMAND_PALETTE_BINDING = "ctrl+backslash"
    COMMAND_PALETTE_DISPLAY = "ctrl+\\"

    def compose(self) -> ComposeResult:
        yield Footer()


if __name__ == "__main__":
    app = NewPaletteBindingApp()
    app.run()
