from anytext.app import App, ComposeResult
from anytext.widgets import TextArea
from anytext.widgets.text_area import Selection

TEXT = """\
def hello(name):
    print("hello" + name)

def goodbye(name):
    print("goodbye" + name)
"""


class TextAreaSelection(App):
    def compose(self) -> ComposeResult:
        text_area = TextArea.code_editor(TEXT, language="python")
        text_area.selection = Selection(start=(0, 0), end=(2, 0))  # (1)!
        yield text_area


app = TextAreaSelection()
if __name__ == "__main__":
    app.run()
