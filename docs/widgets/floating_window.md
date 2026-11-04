# FloatingWindow

A floating container that you can resize by dragging its border. Drag an edge
to resize one dimension, or a corner to resize both. Hold Alt while dragging
anywhere inside the window with the left mouse button to move it. Alt+right-drag
resizes from the nearest corner to the initial click.
The opposite corner stays fixed throughout the drag.

The optional `title` appears in the existing top
border and takes no extra row. Omit it for an untitled window.

```python
from anytext.widgets import FloatingWindow, TextArea

with FloatingWindow(title="Editor", id="editor"):
    yield TextArea("Hello, Anytext!")
```

Use CSS to set the initial size and position, and any minimum or maximum size:

```css
Screen { layers: background floating-windows; }
#editor {
    width: 44;
    height: 15;
    offset: 3 3;
    min-width: 16;
    min-height: 5;
    max-width: 80%;
}
```

Windows use absolute positioning within their parent, leaving surrounding layout
unchanged. Use a parent with an explicit height when putting windows inside
another container. The `floating-windows` layer can be included in the parent's
`layers` to place windows above background widgets.

Windows can move past their parent's edges; the parts outside the parent's
content area are clipped and do not receive mouse input. Moving or resizing keeps
at least three columns and two rows inside the parent, so you can grab the window
again after releasing the mouse. For smaller windows or parents, the grab area
shrinks to the available size. Captured dragging continues outside the parent.
Resizing is constrained to the parent and respects CSS size limits. If the parent
is smaller than a window's minimum size, that minimum takes priority.
Dragging sets cell dimensions and offsets as inline styles. Escape during a drag
restores the previous CSS geometry. Releasing the mouse keeps the new geometry.

The modifier for both gestures is configurable with `move_modifier="alt"` (the default),
`"ctrl"`, or `"shift"`. It is detected from the mouse event, so the terminal or
browser must forward that modifier. `resizable=False` disables both border and
modifier-right-drag resizing; `movable=False` disables modifier-left-drag movement. Ordinary content interactions,
such as clicking a button or selecting text, continue to work without the move
modifier. Removing the CSS border removes the ordinary edge resize targets;
modifier-right-drag resizing remains available.

Run the example:

```sh
python docs/examples/widgets/floating_window.py
```

```python
--8<-- "docs/examples/widgets/floating_window.py"
```

::: anytext.widgets.FloatingWindow
    options:
      show_root_heading: true
      heading_level: 2
