from anytext import events
from anytext.app import App, ComposeResult
from anytext.widgets import TextArea


class ExtendedTextArea(TextArea):
    """A subclass of TextArea with parenthesis-closing functionality."""

    def _on_key(self, event: events.Key) -> None:
        if event.character == "(":
            self.insert("()")
            self.move_cursor_relative(columns=-1)
            event.prevent_default()


class TextAreaKeyPressHook(App):
    def compose(self) -> ComposeResult:
        yield ExtendedTextArea.code_editor(language="python")


app = TextAreaKeyPressHook()
if __name__ == "__main__":
    app.run()
