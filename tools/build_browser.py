"""Build a static Pyodide demo that can be hosted on GitHub Pages."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from shutil import copy2


def build_browser_site(output: Path) -> None:
    """Bundle browser assets and this checkout's wheel with relative URLs."""
    from poetry.core.masonry.api import build_wheel

    repo = Path(__file__).resolve().parent.parent
    output = output.resolve()
    wheels = output / "wheels"
    wheels.mkdir(parents=True, exist_ok=True)
    previous = Path.cwd()
    try:
        os.chdir(repo)
        wheel = build_wheel(str(wheels))
    finally:
        os.chdir(previous)

    for name in ("index.html", "browser.js", "app.py"):
        copy2(repo / "examples" / "browser" / name, output / name)
    (output / "wheel.json").write_text(
        json.dumps({"wheel": f"wheels/{wheel}"}) + "\n", encoding="utf-8"
    )
    (output / ".nojekyll").touch()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".cache/browser-site"))
    args = parser.parse_args()
    try:
        build_browser_site(args.output)
    except ImportError:
        parser.error("Install the build backend: python -m pip install poetry-core")
    print(f"Built static demo in {args.output.resolve()}", flush=True)


if __name__ == "__main__":
    main()
