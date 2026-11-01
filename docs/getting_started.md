# Getting started with Anytext

Anytext is a fork of [Textual](https://github.com/Textualize/textual) for building
terminal user interfaces. It requires Python 3.11 or later and runs on Linux,
macOS, and Windows.

## Installation

```sh
pip install anytext
```

For syntax highlighting in the [TextArea](widgets/text_area.md) widget:

```sh
pip install "anytext[syntax]"
```

To install a local checkout for development, run `pip install -e .` from the
repository root.

## Demo

```sh
python -m anytext
```

## Examples

From the repository root, run an example:

```sh
python examples/calculator.py
```

The `examples` and `docs/examples` directories contain additional apps and widget
examples. Import the framework with `from anytext.app import App` and use
`anytext.widgets` for widgets.

## Configuration

Use `ANYTEXT_*` environment variables for settings, such as `ANYTEXT_THEME`,
`ANYTEXT_ANIMATIONS`, and `ANYTEXT_FPS`. Built-in themes are named `anytext-dark`
and `anytext-light`. Feature flags use `ANYTEXT`.

The logging handler is `anytext.logging.AnytextHandler`, and framework CSS classes
use the `anytext` prefix. Upstream developer tools and snapshot plugins are
external integrations and may require adaptation before use with Anytext.
