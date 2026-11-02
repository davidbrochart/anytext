# Thread-free hosts and WebAssembly

Anytext supports running on one event loop without Python threads or socket
pairs. This mode is selected automatically on Emscripten (including Pyodide) and
WASI. On a desktop, set `ANYTEXT_THREADS=0` **before importing Anytext** to exercise
the same path.

On WASM, the default driver in this mode is `CallbackDriver`. It uses no native
terminal APIs. The host provides input strings and dimensions; the driver sends ANSI
output to a synchronous callback. A terminal emulator such as xterm.js can
consume that output.

## Run a desktop demo without threads

On Linux or macOS, install this checkout and run:

```sh
python -m pip install -e .
ANYTEXT_THREADS=0 python -m anytext
```

This selects `LinuxAsyncDriver`, which reads terminal input using AnyIO readiness
notifications on the app loop and writes output directly. It does not create
input/output threads. Keyboard, mouse, resize notifications, and parser timeouts
use the same terminal setup and event processing as the existing desktop driver.
A slow output device can pause the app while a synchronous write completes.

Use `ANYTEXT_THREADS=0 python examples/calculator.py` for a smaller example.
Native Windows console input is not yet supported without threads; the
host-driven `CallbackDriver` remains available there. Browser/WASM hosts still
use `CallbackDriver`, without native terminal APIs.

## Try it in your browser

The [hosted browser demo](https://davidbrochart.github.io/anytext/) runs entirely
in your browser, with no Python server.

From the repository root:

```sh
python -m pip install poetry-core
python tools/serve_browser.py
```

Open **http://127.0.0.1:8000/**. The server builds this checkout into a temporary
wheel; the browser installs that wheel into Pyodide and renders the app with
xterm.js. No published Anytext package is used. Internet access is required to
load Pyodide, xterm.js, and Python dependencies; first startup may take a moment.

Type a message and press Enter, activate Count with the mouse or Tab/Enter,
resize the window, and use Quit (or Ctrl+Q) to check shutdown. Reload starts a
fresh interpreter. You can edit `examples/browser/app.py` and reload to try your
own widgets. After changes under `src/anytext`, restart the server to rebuild the
wheel. Use `--port 8001` if port 8000 is occupied.

### Static hosting and GitHub Pages

Build a directory that can be served by any static web host:

```sh
python -m pip install poetry-core
python tools/build_browser.py --output .cache/browser-site
python -m http.server --directory .cache/browser-site 8000
```

The directory includes the demo, a wheel built from this checkout, and a package
manifest with relative URLs. It works at both a site root and a project path
such as `/anytext/`. You can preview the project path locally with
`python tools/serve_browser.py --base-path anytext`.

The `Browser demo on GitHub Pages` workflow builds and deploys this directory
after relevant pushes to `main`, or when run manually. Enable it once in the
repository's **Settings → Pages → Build and deployment → Source → GitHub Actions**.
The expected URL is `https://davidbrochart.github.io/anytext/`.

## Connect a terminal

Supply a driver factory to your app. The host must call `feed_input()` and
`resize()` on the app's event-loop thread, and the output callback must return
promptly.

```python
from anytext.app import App, ComposeResult
from anytext.drivers.callback_driver import CallbackDriver
from anytext.widgets import Input


driver = None


def make_driver(app, **options):
    global driver
    driver = CallbackDriver(app, output=terminal_write, **options)
    return driver


def feed_input(data):
    if driver is not None:
        driver.feed_input(data)


def resize(width, height):
    if driver is not None:
        driver.resize(width, height)


class TerminalApp(App):
    def compose(self) -> ComposeResult:
        yield Input(placeholder="Type here")


app = TerminalApp(driver_class=make_driver)
```

Here `terminal_write` is supplied by the host. In a browser, after installing
Anytext and loading these definitions into Pyodide, the JavaScript side can be:

```javascript
// term is an initialized xterm.js terminal, and pythonSource is the code above.
pyodide.globals.set("terminal_write", (data) => term.write(data));
pyodide.runPython(pythonSource);
const feedInput = pyodide.globals.get("feed_input");
const resize = pyodide.globals.get("resize");
const inputSubscription = term.onData((data) => feedInput(data));
const resizeSubscription = term.onResize(({cols, rows}) => resize(cols, rows));

try {
  await pyodide.runPythonAsync("await app.run_async(size=(80, 24))");
} finally {
  inputSubscription.dispose();
  resizeSubscription.dispose();
  feedInput.destroy();
  resize.destroy();
}
```

Use `await app.run_async()` in Pyodide's existing event loop. Do not start a
second loop with `app.run()` or `anyio.run()`. If Pyodide runs in a Web Worker,
forward terminal input, resize events, and output through worker messages.

`feed_input()` accepts decoded strings, including escape sequences and bracketed
paste. The driver checks parser timeouts on an async task, so a lone Escape key
works without a subsequent input event. Shutdown cancels that task and restores
terminal modes.

## Workers and synchronous work

Async workers continue to work. Explicit `thread=True` workers raise
`WorkerError` in thread-free mode; they are never silently executed on the UI
loop. Convert application workers to async functions and await host I/O.

Built-in Markdown parsing and file loading, directory loading, log width
calculation, demo source loading, and file delivery can run without threads.
Synchronous operations execute on the app loop, with cancellation checkpoints
before and after them. Large files, directories, or expensive parsing can still
pause the UI during the synchronous operation. Files refer to the host runtime's
filesystem; saving a file in Pyodide does not itself trigger a browser download.

The original threaded desktop drivers and explicit thread workers remain available
when threads are enabled. They are rejected in thread-free mode. Browser networking,
native extension wheels, and the full demo's external services have their own
WASM compatibility requirements; this mode does not emulate those services.

## Verification

`tests/test_thread_free.py` forbids thread creation, AnyIO thread offloads, and
socket pairs while exercising widgets, terminal input/output, resize, parser
timeouts, file delivery, cancellation, and shutdown.

The permanent Chromium regression test builds and serves this checkout, then
checks real browser input, keyboard/mouse buttons, resizing, shutdown, and the
thread/socket guards:

```sh
python -m pip install poetry-core
npm ci --prefix tests/browser
npm run install-browser --prefix tests/browser
npm test --prefix tests/browser
```

See `tests/browser/README.md` for environment selection and failure diagnostics. The `Browser tests` CI workflow runs the same
test and retains screenshots, traces, and logs when it fails.

To run the smoke test in real Pyodide under Node, install the `pyodide` npm
package outside this repository and point the script at a Python environment
containing Anytext's pure-Python dependencies:

```sh
npm install --prefix /tmp/anytext-wasm pyodide
NODE_PATH=/tmp/anytext-wasm/node_modules node tools/check_pyodide.cjs /path/to/site-packages
```

This runs `tests/wasm/smoke.py` in Emscripten Python. It checks automatic mode
selection without setting `ANYTEXT_THREADS`, and replaces thread and socket
entry points with functions that fail immediately.
