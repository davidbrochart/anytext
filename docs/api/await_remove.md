---
title: "anytext.await_remove"
---

This module contains the `AwaitRemove` class.
An `AwaitRemove` object is returned by [`Widget.remove()`][anytext.widget.Widget.remove] and other methods which remove widgets.
You can await the return value if you need to know exactly when the widget(s) have been removed.
Or you can ignore it and Anytext will wait for the widgets to be removed before handling the next message.

!!! note

    You are unlikely to need to explicitly create these objects yourself.


::: anytext.await_remove
