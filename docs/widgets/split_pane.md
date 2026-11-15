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

### Moving a live widget into a split

Use [`Widget.reparent()`][anytext.widget.Widget.reparent] to move an already
mounted widget into a pane without restarting its workers or timers or losing
its state. Create pane containers explicitly so they can receive existing widgets:

```python
from anytext.containers import Vertical
from anytext.widgets import SplitPane

left = Vertical()
right = Vertical()
split = SplitPane(left, right)
await self.mount(split)
existing_editor.reparent(left)
```

The existing widget and destination must both be mounted on the same screen.
The move does not send mount or unmount events, and messages now bubble through
the new parent. Focus stays on the moved widget or its descendant unless the
new ancestry makes it hidden or disabled. CSS and layout follow the new ancestry.

Use `widget.reparent(container, before="#sibling")` or `after=...` to choose a
position among the new parent's children. With no insertion point, the widget is
appended. Reparent widgets you want to keep before removing their old container.

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

## Modifier-drag gestures

Like `FloatingWindow`, split panes accept modifier gestures over their content,
including interactive buttons and text editors:

- **Alt+right-drag** inside a pane resizes from its nearest corner. Each axis
  adjusts the nearest split bounding that edge; outside screen edges stay fixed. In nested layouts, horizontal motion can resize an ancestor's column
  while vertical motion resizes the inner row. Panes sharing that column or row
  resize together. Escape restores all affected split ratios.
- **Alt+left-drag** a pane onto another pane to exchange their content widgets.
  This works across nested splits and preserves widget state, workers, and timers.
  Dropping back onto the same pane or outside a pane leaves the layout unchanged.
- **Escape** cancels the current gesture. Disabling, hiding, removing, or resizing
  a split during a drag releases mouse capture.

These gestures also work when `show_divider=False`. Ordinary clicks, text
selection, and direct divider dragging retain their usual behavior. Set
`drag_modifier="ctrl"` or `"shift"` if Alt-mouse is reserved by the desktop.
Set `swappable=False` to disable pane swaps while retaining modifier resizing.

After a swap, `SplitPane.first` and `.second` refer to the new content widgets.
A `SplitPane.Swapped` message identifies the source `split_pane`, destination
`other`, and the two exchanged widgets, `pane` and `other_pane`, so hosts can
update their own pane ordering or session models. Ancestor panes cannot be
swapped into their own descendants.

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

During modifier-left-drag, a floating snapshot of the pane follows the pointer. Release over another pane to swap them, or press Escape to cancel. The live content stays mounted throughout the drag.
