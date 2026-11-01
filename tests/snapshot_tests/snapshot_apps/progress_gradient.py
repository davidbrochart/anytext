from anytext.app import App, ComposeResult
from anytext.color import Gradient
from anytext.widgets import ProgressBar


class ProgressApp(App[None]):
    def compose(self) -> ComposeResult:
        gradient = Gradient.from_colors(
            "#881177",
            "#aa3355",
            "#cc6666",
            "#ee9944",
            "#eedd00",
            "#99dd55",
            "#44dd88",
            "#22ccbb",
            "#00bbcc",
            "#0099cc",
            "#3366bb",
            "#663399",
        )
        yield ProgressBar(total=100, gradient=gradient)

    def on_mount(self) -> None:
        self.query_one(ProgressBar).update(progress=50)


if __name__ == "__main__":
    ProgressApp().run()
