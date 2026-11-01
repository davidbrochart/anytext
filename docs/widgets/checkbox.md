# Checkbox

!!! tip "Added in version 0.13.0"

A simple checkbox widget which stores a boolean value.

- [x] Focusable
- [ ] Container

## Example

The example below shows check boxes in various states.

=== "Output"

    ```{.anytext path="docs/examples/widgets/checkbox.py"}
    ```

=== "checkbox.py"

    ```python
    --8<-- "docs/examples/widgets/checkbox.py"
    ```

=== "checkbox.tcss"

    ```css
    --8<-- "docs/examples/widgets/checkbox.tcss"
    ```

## Reactive Attributes

| Name    | Type   | Default | Description                |
| ------- | ------ | ------- | -------------------------- |
| `value` | `bool` | `False` | The value of the checkbox. |

## Messages

- [Checkbox.Changed][anytext.widgets.Checkbox.Changed]

## Bindings

The checkbox widget defines the following bindings:

::: anytext.widgets._toggle_button.ToggleButton.BINDINGS
    options:
      show_root_heading: false
      show_root_toc_entry: false

## Component Classes

The checkbox widget inherits the following component classes:

::: anytext.widgets._toggle_button.ToggleButton.COMPONENT_CLASSES
    options:
      show_root_heading: false
      show_root_toc_entry: false


---


::: anytext.widgets.Checkbox
    options:
      heading_level: 2
