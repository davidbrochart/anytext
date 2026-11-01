---
title: "Why doesn't Anytext support ANSI themes?"
alt_titles:
  - "Anytext should use system terminal colors for cyan, etc"
  - "ANSI theme colors not working"
---

Anytext will not generate escape sequences for the 16 themeable *ANSI* colors.

This is an intentional design decision we took for the following reasons:

- Not everyone has a carefully chosen ANSI color theme. Color combinations which may look fine on your system, may be unreadable on another machine. There is very little an app author or Anytext can do to resolve this. Asking users to simply pick a better theme is not a good solution, since not all users will know how.
- ANSI colors can't be manipulated in the way Anytext can do with other colors. Anytext can blend colors and produce light and dark shades from an original color, which is used to create more readable text and user interfaces. Color blending will also be used to power future accessibility features.

Anytext has a design system which guarantees apps will be readable on all platforms and terminals, and produces better results than ANSI colors.

There is currently a light and dark version of the design system, but more are planned. It will also be possible for users to customize the source colors on a per-app or per-system basis. This means that in the future you will be able to modify the core colors to blend in with your chosen terminal theme.

!!! tip "Changed in version 0.80.0"

    Anytext added an `ansi_color` boolean to App. If you set this to `True`, then Anytext will not attempt to convert ANSI colors. Note that you will lose transparency effects if you enable this setting.
