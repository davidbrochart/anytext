from rich.syntax import Syntax

from anytext.app import App, ComposeResult, RenderResult
from anytext.reactive import reactive
from anytext.widget import Widget


class CodeView(Widget):
    """Widget to display Python code."""

    DEFAULT_CSS = """
    CodeView { height: auto; }
    """

    code = reactive("")

    def render(self) -> RenderResult:
        # Syntax is a Rich renderable that displays syntax highlighted code
        syntax = Syntax(self.code, "python", line_numbers=True, indent_guides=True)
        return syntax


class CodeApp(App):
    """App to demonstrate Rich renderables in Anytext."""

    def compose(self) -> ComposeResult:
        with open(__file__) as self_file:
            code = self_file.read()
        code_view = CodeView()
        code_view.code = code
        yield code_view


if __name__ == "__main__":
    app = CodeApp()
    app.run()
