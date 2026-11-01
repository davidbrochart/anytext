from anytext import on, work
from anytext.app import App, ComposeResult
from anytext.screen import Screen
from anytext.widgets import Button, Label


class QuestionScreen(Screen[bool]):
    """Screen with a parameter."""

    def __init__(self, question: str) -> None:
        self.question = question
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Label(self.question)
        yield Button("Yes", id="yes", variant="success")
        yield Button("No", id="no")

    @on(Button.Pressed, "#yes")
    def handle_yes(self) -> None:
        self.dismiss(True)  # (1)!

    @on(Button.Pressed, "#no")
    def handle_no(self) -> None:
        self.dismiss(False)  # (2)!


class QuestionsApp(App):
    """Demonstrates wait_for_dismiss"""

    CSS_PATH = "questions01.tcss"

    @work  # (3)!
    async def on_mount(self) -> None:
        if await self.push_screen_wait(  # (4)!
            QuestionScreen("Do you like Anytext?"),
        ):
            self.notify("Good answer!")
        else:
            self.notify(":-(", severity="error")


if __name__ == "__main__":
    app = QuestionsApp()
    app.run()
