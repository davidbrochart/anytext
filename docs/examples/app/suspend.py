from os import system

from anytext import on
from anytext.app import App, ComposeResult
from anytext.widgets import Button


class SuspendingApp(App[None]):

    def compose(self) -> ComposeResult:
        yield Button("Open the editor", id="edit")

    @on(Button.Pressed, "#edit")
    def run_external_editor(self) -> None:
        with self.suspend():  # (1)!
            system("vim")


if __name__ == "__main__":
    SuspendingApp().run()
