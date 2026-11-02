# Browser regression test

This test runs the bundled `DemoApp` in headless Chromium with actual
Pyodide/WASM and xterm.js. It starts and stops its own server on an available
localhost port; it does not require the demo server to be running already.
The server uses the static site builder and serves the demo under `/anytext/`,
so the same test verifies GitHub Pages project paths and relative wheel URLs.

From the repository root, using Node.js 20 or later:

```sh
python -m pip install poetry-core
npm ci --prefix tests/browser
npm run install-browser --prefix tests/browser
npm test --prefix tests/browser
```

On Linux, install Chromium's system dependencies if necessary:

```sh
cd tests/browser
npx playwright install --with-deps chromium
```

Set `ANYTEXT_TEST_PYTHON` to a Python executable with `poetry-core` installed if
`python` on PATH is not the right environment. For example:

```sh
ANYTEXT_TEST_PYTHON="$PWD/.venv/bin/python" npm test --prefix tests/browser
```

`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` optionally selects an existing Chromium
binary; otherwise Playwright uses the browser installed by `install-browser`.
Internet access is required for the demo's pinned Pyodide/xterm.js assets and
Python dependencies. This is an integration test and is separate from pytest.

If the system temporary directory is full or quota-limited, point `TMPDIR` at a
writable directory with sufficient space (on Unix):

```sh
mkdir -p .cache/browser-tmp
TMPDIR="$PWD/.cache/browser-tmp" npm test --prefix tests/browser
```

## Coverage

The test checks:

- Loading the wheel built from this checkout into real Emscripten Python.
- Loading static assets and the wheel under a GitHub Pages project path.
- Startup without Python thread creation, AnyIO thread offloads, or socket pairs.
- The official Home screen and source-code viewer.
- Widgets screen input and button activation through keyboard and terminal mouse events.
- Project links through the browser host and SVG screenshot downloads.
- Game setup and the async shuffle worker.
- Propagation of browser terminal width and height changes to Anytext.
- Shutdown, cancellation of the parser task, and removal of the app runtime.
- Unhandled JavaScript errors, browser console errors, and failed requests.

On failure, `test-results/` contains a screenshot and Playwright trace alongside
server and browser error logs. View a trace with:

```sh
cd tests/browser
npx playwright show-trace test-results/trace.zip
```

The `Browser tests` GitHub Actions workflow runs this test for relevant changes
and uploads failure diagnostics. The WASM smoke test under Node remains available
through `tools/check_pyodide.cjs`; it does not replace the Chromium test.
