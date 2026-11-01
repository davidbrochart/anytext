"""Build this checkout and serve the Pyodide browser example on localhost."""

from __future__ import annotations

import argparse
import json
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    try:
        from poetry.core.masonry.api import build_wheel
    except ImportError:
        parser.error(
            "Install the build backend first: python -m pip install poetry-core"
        )

    repo = Path(__file__).resolve().parent.parent
    with TemporaryDirectory(prefix="anytext-browser-") as temporary:
        # Poetry's build API builds the current working directory.
        import os

        previous = Path.cwd()
        try:
            os.chdir(repo)
            wheel = build_wheel(temporary)
        finally:
            os.chdir(previous)
        wheel_path = Path(temporary) / wheel

        class Handler(SimpleHTTPRequestHandler):
            def do_GET(self) -> None:
                path = urlsplit(self.path).path
                if path == "/wheel.json":
                    self.send_bytes(
                        json.dumps({"wheel": f"/wheels/{wheel}"}).encode(),
                        "application/json",
                    )
                elif path == f"/wheels/{wheel}":
                    self.send_bytes(wheel_path.read_bytes(), "application/octet-stream")
                else:
                    super().do_GET()

            def send_bytes(self, data: bytes, content_type: str) -> None:
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)

        handler = partial(Handler, directory=str(repo / "examples" / "browser"))
        with HTTPServer(("127.0.0.1", args.port), handler) as server:
            print(f"Open http://127.0.0.1:{server.server_port}/", flush=True)
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
