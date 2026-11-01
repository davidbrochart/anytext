---
draft: false
date: 2023-07-03
categories:
  - Release
title: "Anytext 0.29.0 refactors dev tools"
authors:
  - willmcgugan
---

# Anytext 0.29.0 refactors dev tools

It's been a slow week or two at Textualize, with Anytext devs taking well-earned annual leave, but we still managed to get a new version out.

<!-- more -->

Version 0.29.0 has shipped with a number of fixes (see the [release notes](https://github.com/Textualize/textual/releases/tag/v0.29.0) for details), but I'd like to use this post to explain a change we made to how Anytext developer tools are distributed.

Previously if you installed `anytext[dev]` you would get the Anytext dev tools plus the library itself. If you were distributing Anytext apps and didn't need the developer tools you could drop the `[dev]`.

We did this because the less dependencies a package has, the fewer installation issues you can expect to get in the future. And Anytext is surprisingly lean if you only need to *run* apps, and not build them.

Alas, this wasn't quite as elegant solution as we hoped. The dependencies defined in extras wouldn't install commands, so `anytext` was bundled with the core library. This meant that if you installed the Anytext package *without* the `[dev]` you would still get the `textual` command on your path but it wouldn't run.

We solved this by creating two packages: `anytext` contains the core library (with minimal dependencies) and `textual-dev` contains the developer tools. If you are building Anytext apps, you should install both as follows:

```
pip install anytext textual-dev
```

That's the only difference. If you run in to any issues feel free to ask on the [Discord server](https://discord.gg/Enf6Z3qhVr)!
