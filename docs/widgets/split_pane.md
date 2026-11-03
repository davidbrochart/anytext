# SplitPane

Two panes separated by a draggable divider. Each pane can contain any widget,
including another `SplitPane` for more complex layouts.

- [x] Container
- [x] Focusable divider

## Example

```python
from anytext.widgets import SplitPane, TextArea

yield SplitPane(
    TextArea("Left editor"),
    TextArea("Right editor"),
    position=0.4,
    min_first=12,
    min_second=12,
)
```

`orientation="horizontal"` (the default) places panes side by side, with a vertical
divider. `orientation="vertical"` stacks them, with a horizontal divider.
`position` is the preferred fraction of available space allocated to the first
pane, excluding the one-cell divider when visible. It must be between `0` and `1`.

`min_first` and `min_second` specify minimum pane sizes in columns for horizontal
splits, or rows for vertical splits. If the terminal becomes too small for both
minima, the remaining space is shared in proportion to the minima. The preferred
ratio is retained and restored as space becomes available again.

Pane content keeps its own styles; internal wrappers control each pane's size
and clip content that no longer fits. Set the minimum sizes to suit your widgets:
for example, a pane with a one-cell border, one-cell padding on all sides, and
one row of text needs a minimum height of five rows.

### Invisible divider with no gap

```python
SplitPane(left_widget, right_widget, show_divider=False)
```

With `show_divider=False`, the panes meet directly and share all available space.
An invisible one-cell drag target overlays the last column or row of the first
pane, rather than taking an extra column or row. If the first pane is collapsed,
the handle sits at the start of the second pane instead. No line or background
is painted over the content, including on hover and keyboard focus.

That edge cell handles resize gestures instead of clicks on the content beneath
it. Mouse dragging and keyboard controls otherwise behave as for a visible
divider. Set `split.show_divider = True` to show it again; changing this option
preserves the preferred ratio and ends any active drag.

### Runnable example

```sh
python docs/examples/widgets/split_pane.py
```

```python
--8<-- "docs/examples/widgets/split_pane.py"
```

## Interaction

Drag the divider with the left mouse button. Mouse capture keeps the drag active
when the pointer leaves the divider. Release the button to finish, or press
Escape to cancel the drag and restore its starting position.

Tab can focus a divider. Left/Right adjust horizontal splits by one column;
Up/Down adjust vertical splits by one row. Home/End move to the minimum/maximum
allowed position. Enter restores the initial ratio. Escape removes focus when
not dragging. You can focus a specific divider with `split.divider.focus()`.

Mouse support depends on the terminal. The browser demo also supports dragging.

## Messages and properties

`SplitPane.Changed` is posted when actual pane sizes change, including on a
terminal resize. It exposes `split_pane`, `first_size`, `second_size`, and
`position` (the actual first-pane fraction after applying minimum sizes).
`control` is an alias for `split_pane`.

The widget's reactive `position` is the preferred ratio; `first_size` and
`second_size` are its current sizes in cells. `orientation`, `min_first`, and
`min_second` can also be changed while running. `first` and `second` refer to the
supplied content widgets.

Disabling the split disables its content and divider. Disabling, removing, or
resizing a split during a drag releases mouse capture.

## Styling

The internal widgets have the classes `split-pane--first`, `split-pane--second`,
and `split-pane--divider`. The divider highlights on focus, hover, and dragging.

## API

::: anytext.widgets.SplitPane
    options:
      show_root_heading: true
      heading_level: 3
