from anytext.app import App, ComposeResult
from anytext.widgets import TextArea

TEXT = """\
def hello(name):
    print("hello" + name)

def goodbye(name):
    print("goodbye" + name)
"""


class TextAreaExample(App):
    def compose(self) -> ComposeResult:
        yield TextArea.code_editor(TEXT, language="python")


app = TextAreaExample()
if __name__ == "__main__":
    app.run()
