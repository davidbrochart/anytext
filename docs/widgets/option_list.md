# OptionList

!!! tip "Added in version 0.17.0"

A widget for showing a vertical list of Rich renderable options.

- [x] Focusable
- [ ] Container

## Examples

### Options as simple strings

An `OptionList` can be constructed with a simple collection of string
options:

=== "Output"

    ```{.anytext path="docs/examples/widgets/option_list_strings.py"}
    ```

=== "option_list_strings.py"

    ~~~python
    --8<-- "docs/examples/widgets/option_list_strings.py"
    ~~~

=== "option_list.tcss"

    ~~~css
    --8<-- "docs/examples/widgets/option_list.tcss"
    ~~~

### Options as `Option` instances

For finer control over the options, the `Option` class can be used; this
allows for setting IDs, setting initial disabled state, etc. The `Separator`
class can be used to add separator lines between options.

=== "Output"

    ```{.anytext path="docs/examples/widgets/option_list_options.py"}
    ```

=== "option_list_options.py"

    ~~~python
    --8<-- "docs/examples/widgets/option_list_options.py"
    ~~~

=== "option_list.tcss"

    ~~~css
    --8<-- "docs/examples/widgets/option_list.tcss"
    ~~~

### Options as Rich renderables

Because the prompts for the options can be [Rich
renderables](https://rich.readthedocs.io/en/latest/protocol.html), this
means they can be any height you wish. As an example, here is an option list
comprised of [Rich
tables](https://rich.readthedocs.io/en/latest/tables.html):

=== "Output"

    ```{.anytext path="docs/examples/widgets/option_list_tables.py"}
    ```

=== "option_list_tables.py"

    ~~~python
    --8<-- "docs/examples/widgets/option_list_tables.py"
    ~~~

=== "option_list.tcss"

    ~~~css
    --8<-- "docs/examples/widgets/option_list.tcss"
    ~~~

## Reactive Attributes

| Name          | Type            | Default | Description                                                               |
| ------------- | --------------- | ------- | ------------------------------------------------------------------------- |
| `highlighted` | `int` \| `None` | `None`  | The index of the highlighted option. `None` means nothing is highlighted. |

## Messages

- [OptionList.OptionHighlighted][anytext.widgets.OptionList.OptionHighlighted]
- [OptionList.OptionSelected][anytext.widgets.OptionList.OptionSelected]

Both of the messages above inherit from the common base [`OptionList.OptionMessage`][anytext.widgets.OptionList.OptionMessage], so refer to its documentation to see what attributes are available.

## Bindings

The option list widget defines the following bindings:

::: anytext.widgets.OptionList.BINDINGS
    options:
      show_root_heading: false
      show_root_toc_entry: false

## Component Classes

The option list provides the following component classes:

::: anytext.widgets.OptionList.COMPONENT_CLASSES
    options:
      show_root_heading: false
      show_root_toc_entry: false



::: anytext.widgets.OptionList
    options:
      heading_level: 2


::: anytext.widgets.option_list
    options:
      heading_level: 2
