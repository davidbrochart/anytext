# Switch

A simple switch widget which stores a boolean value.

- [x] Focusable
- [ ] Container

## Example

The example below shows switches in various states.

=== "Output"

    ```{.anytext path="docs/examples/widgets/switch.py"}
    ```

=== "switch.py"

    ```python
    --8<-- "docs/examples/widgets/switch.py"
    ```

=== "switch.tcss"

    ```css
    --8<-- "docs/examples/widgets/switch.tcss"
    ```

## Reactive Attributes

| Name    | Type   | Default | Description              |
| ------- | ------ | ------- | ------------------------ |
| `value` | `bool` | `False` | The value of the switch. |

## Messages

- [Switch.Changed][anytext.widgets.Switch.Changed]

## Bindings

The switch widget defines the following bindings:

::: anytext.widgets.Switch.BINDINGS
    options:
      show_root_heading: false
      show_root_toc_entry: false

## Component Classes

The switch widget provides the following component classes:

::: anytext.widgets.Switch.COMPONENT_CLASSES
    options:
      show_root_heading: false
      show_root_toc_entry: false

## Additional Notes

- To remove the spacing around a `Switch`, set `border: none;` and `padding: 0;`.

---


::: anytext.widgets.Switch
    options:
      heading_level: 2
