from anytext.app import App, ComposeResult
from anytext.widgets import Tree


class TreeApp(App):
    def compose(self) -> ComposeResult:
        tree: Tree[str] = Tree("Dune")
        tree.root.expand()
        characters = tree.root.add("Characters", expand=True)
        characters.add_leaf("Paul")
        characters.add_leaf("Jessica")
        characters.add_leaf("Chani")
        yield tree


if __name__ == "__main__":
    app = TreeApp()
    app.run()
