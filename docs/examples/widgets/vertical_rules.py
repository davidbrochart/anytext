from anytext.app import App, ComposeResult
from anytext.containers import Horizontal
from anytext.widgets import Label, Rule


class VerticalRulesApp(App):
    CSS_PATH = "vertical_rules.tcss"

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("solid")
            yield Rule(orientation="vertical")
            yield Label("heavy")
            yield Rule(orientation="vertical", line_style="heavy")
            yield Label("thick")
            yield Rule(orientation="vertical", line_style="thick")
            yield Label("dashed")
            yield Rule(orientation="vertical", line_style="dashed")
            yield Label("double")
            yield Rule(orientation="vertical", line_style="double")
            yield Label("ascii")
            yield Rule(orientation="vertical", line_style="ascii")


if __name__ == "__main__":
    app = VerticalRulesApp()
    app.run()
