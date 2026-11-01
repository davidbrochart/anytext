# Anytext

Anytext is a fork of [Textual](https://github.com/Textualize/textual), a Python framework for building terminal user interfaces.

## Installation

```sh
pip install anytext
```

To install this checkout for development:

```sh
pip install -e .
```

## Usage

```python
from anytext.app import App, ComposeResult
from anytext.widgets import Header, Footer, Static


class HelloApp(App):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Hello from Anytext!")
        yield Footer()


if __name__ == "__main__":
    HelloApp().run()
```

Run the bundled demo with `python -m anytext`.

Configuration uses `ANYTEXT_*` environment variables, including `ANYTEXT_THEME`,
`ANYTEXT_ANIMATIONS`, and `ANYTEXT_FPS`. The default themes are `anytext-dark` and
`anytext-light`. Set feature flags with `ANYTEXT` (for example, `ANYTEXT=debug`).

Upstream tools such as `textual-dev`, `textual-serve`, and
`pytest-textual-snapshot` are external packages and may require adaptation for
this fork. External package names and links keep their original names.

## License and attribution

Anytext retains the original MIT license and original copyright notices. See [LICENSE](LICENSE).
