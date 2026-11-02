"""Build this checkout and serve the Pyodide browser example on localhost."""

from __future__ import annotations

import argparse
import re
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from tempfile import TemporaryDirectory

from build_browser import build_browser_site


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--base-path", default="", help="Serve under a project path, e.g. anytext"
    )
    args = parser.parse_args()
    base_path = args.base_path.strip("/")
    if base_path and not re.fullmatch(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*", base_path):
        parser.error("--base-path must contain ordinary directory names")

    with TemporaryDirectory(prefix="anytext-browser-") as temporary:
        try:
            build_browser_site(Path(temporary) / base_path)
        except ImportError:
            parser.error(
                "Install the build backend first: python -m pip install poetry-core"
            )
        handler = partial(SimpleHTTPRequestHandler, directory=temporary)
        with HTTPServer(("127.0.0.1", args.port), handler) as server:
            suffix = f"{base_path}/" if base_path else ""
            print(f"Open http://127.0.0.1:{server.server_port}/{suffix}", flush=True)
            print(
                "Serving this checkout. Internet access is needed for browser dependencies.",
                flush=True,
            )
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()
