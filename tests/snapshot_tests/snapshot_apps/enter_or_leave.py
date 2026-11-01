from anytext import on
from anytext.app import App, ComposeResult
from anytext.widgets import Label
from anytext.widget import Widget
from anytext import events


class MyWidget(Widget):
    def compose(self) -> ComposeResult:
        yield Label("Foo", id="foo")
        yield Label("Bar")

    @on(events.Enter)
    @on(events.Leave)
    def on_enter_or_leave(self):
        self.set_class(self.is_mouse_over, "-over")


class EnterApp(App):
    CSS = """

    MyWidget {
        padding: 2 4;
        background: red;
        height: auto;
        width: auto;
 
        &.-over {
            background: green;
        }
        
        Label {
            background: rgba(20,20,200,0.5);
        }
    }
    """

    def compose(self) -> ComposeResult:
        yield MyWidget()


if __name__ == "__main__":
    app = EnterApp()
    app.run()
