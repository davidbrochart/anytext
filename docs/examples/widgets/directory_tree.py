from anytext.app import App, ComposeResult
from anytext.widgets import DirectoryTree


class DirectoryTreeApp(App):
    def compose(self) -> ComposeResult:
        yield DirectoryTree("./")


if __name__ == "__main__":
    app = DirectoryTreeApp()
    app.run()
