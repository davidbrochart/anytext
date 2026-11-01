from anytext.app import App, ComposeResult
from anytext.widgets import Label, Button


class QuestionApp(App[str]):
    def compose(self) -> ComposeResult:
        yield Label("Do you love Anytext?")
        yield Button("Yes", id="yes", variant="primary")
        yield Button("No", id="no", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.exit(event.button.id)


if __name__ == "__main__":
    app = QuestionApp()
    reply = app.run()
    print(reply)
