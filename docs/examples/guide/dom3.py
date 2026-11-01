from anytext.app import App, ComposeResult
from anytext.containers import Container, Horizontal
from anytext.widgets import Button, Footer, Header, Static

QUESTION = "Do you want to learn about Anytext CSS?"


class ExampleApp(App):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Container(
            Static(QUESTION, classes="question"),
            Horizontal(
                Button("Yes", variant="success"),
                Button("No", variant="error"),
                classes="buttons",
            ),
            id="dialog",
        )


if __name__ == "__main__":
    app = ExampleApp()
    app.run()
