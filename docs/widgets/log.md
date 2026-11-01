# Log

!!! tip "Added in version 0.32.0"

A Log widget displays lines of text which may be appended to in realtime.

Call [Log.write_line][anytext.widgets.Log.write_line] to write a line at a time, or [Log.write_lines][anytext.widgets.Log.write_lines] to write multiple lines at once. Call [Log.clear][anytext.widgets.Log.clear] to clear the Log widget.

!!! tip

    See also [RichLog](../widgets/rich_log.md) which can write more than just text, and supports a number of advanced features.

- [X] Focusable
- [ ] Container

## Example

The example below shows how to write text to a `Log` widget:

=== "Output"

    ```{.anytext path="docs/examples/widgets/log.py"}
    ```

=== "log.py"

    ```python
    --8<-- "docs/examples/widgets/log.py"
    ```



## Reactive Attributes

| Name          | Type   | Default | Description                                                  |
| ------------- | ------ | ------- | ------------------------------------------------------------ |
| `max_lines`   | `int`  | `None`  | Maximum number of lines in the log or `None` for no maximum. |
| `auto_scroll` | `bool` | `False` | Scroll to end of log when new lines are added.               |

## Messages

This widget posts no messages.

## Bindings

This widget has no bindings.

## Component Classes

This widget has no component classes.


---


::: anytext.widgets.Log
    options:
      heading_level: 2
