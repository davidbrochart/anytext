const assert = require("node:assert/strict");
const { spawn } = require("node:child_process");
const { mkdir, unlink, writeFile } = require("node:fs/promises");
const path = require("node:path");
const { once } = require("node:events");
const { before, after, test } = require("node:test");
const { chromium } = require("playwright");

const repo = path.resolve(__dirname, "../..");
const artifacts = path.join(__dirname, "test-results");
let browser;
let server;
let baseURL;
let serverLog = "";

async function startServer() {
  server = spawn(
    process.env.ANYTEXT_TEST_PYTHON || "python",
    [path.join(repo, "tools/serve_browser.py"), "--port", "0"],
    { cwd: repo, stdio: ["ignore", "pipe", "pipe"] },
  );
  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error(`Server startup timed out:\n${serverLog}`)), 30000);
    function record(chunk) {
      serverLog += chunk.toString();
      const match = serverLog.match(/Open (http:\/\/127\.0\.0\.1:\d+\/)/);
      if (match) {
        baseURL = match[1];
        clearTimeout(timeout);
        resolve();
      }
    }
    server.stdout.on("data", record);
    server.stderr.on("data", record);
    server.once("error", (error) => { clearTimeout(timeout); reject(error); });
    server.once("exit", (code) => {
      clearTimeout(timeout);
      reject(new Error(`Server exited (${code}):\n${serverLog}`));
    });
  });
}

before(async () => {
  await mkdir(artifacts, { recursive: true });
  for (const name of ["server.log", "browser-errors.json", "failure.png", "trace.zip"]) {
    await unlink(path.join(artifacts, name)).catch((error) => {
      if (error.code !== "ENOENT") throw error;
    });
  }
  await startServer();
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined,
  });
}, { timeout: 60000 });

after(async () => {
  try {
    await browser?.close();
  } finally {
    if (server?.pid && server.exitCode === null && server.signalCode === null) {
      const exited = once(server, "exit");
      server.kill(process.platform === "win32" ? "SIGTERM" : "SIGINT");
      const killTimeout = setTimeout(() => server.kill("SIGKILL"), 5000);
      try {
        await exited;
      } finally {
        clearTimeout(killTimeout);
      }
    }
    await writeFile(path.join(artifacts, "server.log"), serverLog);
  }
});

const guards = `
import socket
import anyio
forbidden_operations = []
def forbid_thread_or_socket(*args, **kwargs):
    forbidden_operations.append('thread or socket operation')
    raise AssertionError('Browser execution must not create threads or socket pairs')
anyio.to_thread.run_sync = forbid_thread_or_socket
socket.socketpair = forbid_thread_or_socket
`;

function python(page, expression) {
  return page.evaluate((code) => window.anytextDemo.pyodide.runPython(code), expression);
}

function waitForPython(page, expression) {
  return page.waitForFunction(
    (code) => window.anytextDemo.pyodide.runPython(code),
    expression,
    { timeout: 10000 },
  );
}

function waitForTerminalText(page, text) {
  return page.waitForFunction((expected) => {
    const buffer = window.anytextDemo.terminal.buffer.active;
    return Array.from({ length: buffer.length }, (_, index) =>
      buffer.getLine(index).translateToString(),
    ).join("\n").includes(expected);
  }, text, { timeout: 10000 });
}

test("Pyodide runs the local wheel without threads and handles terminal interaction", { timeout: 180000 }, async (t) => {
  const context = await browser.newContext({ viewport: { width: 1200, height: 850 } });
  await context.tracing.start({ screenshots: true, snapshots: true });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(String(error)));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("requestfailed", (request) => errors.push(`${request.url()}: ${request.failure()?.errorText}`));
  const wheelRequests = [];
  page.on("response", (response) => {
    if (response.url().startsWith(`${baseURL}wheels/`)) wheelRequests.push(response);
  });
  await page.route("**/app.py", async (route) => {
    const response = await route.fetch();
    await route.fulfill({ response, body: guards + await response.text() });
  });

  let failed = true;
  try {
    await page.goto(baseURL);
    await page.waitForFunction(() =>
      document.querySelector("#status").textContent.startsWith("Running") ||
      !document.querySelector("#error").hidden,
    null, { timeout: 120000 });
    assert.equal(await page.locator("#error").isVisible(), false,
      await page.locator("#error").textContent());
    assert.equal(await page.locator("#status").textContent(), "Running · Python threads disabled");
    assert.equal(wheelRequests.length, 1, "The checkout's locally built wheel must be loaded");
    assert.equal(wheelRequests[0].status(), 200);
    assert.equal(await python(page, "__import__('sys').platform"), "emscripten");
    assert.equal(await python(page, "constants.THREADS_ENABLED"), false);
    assert.equal(await python(page, "os.environ.get('ANYTEXT_THREADS') is None"), true);
    assert.equal(await python(page, "browser_app._runtime.portal is None"), true);

    const keyboard = page.locator(".xterm-helper-textarea");
    await keyboard.pressSequentially("hello browser");
    await waitForPython(page, "browser_app.query_one(Input).value == 'hello browser'");
    await keyboard.press("Enter");
    await waitForPython(page, "browser_app.query_one(Input).value == ''");
    await waitForTerminalText(page, "You typed: hello browser");
    t.diagnostic("Typing, submission and rendered log output passed");

    await keyboard.press("Tab");
    await keyboard.press("Enter");
    await waitForPython(page, "browser_app.count == 1");
    await waitForTerminalText(page, "Count button pressed: 1");
    // A second press is intentionally ignored during Button's active effect.
    await waitForPython(page, "not browser_app.query_one('#count').has_class('-active')");
    const button = JSON.parse(await python(page,
      "import json; json.dumps(list(browser_app.query_one('#count').region))"));
    const screen = await page.locator(".xterm-screen").boundingBox();
    assert.ok(screen);
    const cells = await page.evaluate(() => ({
      cols: window.anytextDemo.terminal.cols,
      rows: window.anytextDemo.terminal.rows,
    }));
    await page.mouse.click(
      screen.x + (button[0] + button[2] / 2) * screen.width / cells.cols,
      screen.y + (button[1] + button[3] / 2) * screen.height / cells.rows,
    );
    await waitForPython(page, "browser_app.count == 2");
    await waitForTerminalText(page, "Count button pressed: 2");
    t.diagnostic("Keyboard and mouse activation passed");

    await page.setViewportSize({ width: 950, height: 650 });
    await page.waitForFunction((previous) => {
      const { pyodide, terminal } = window.anytextDemo;
      return terminal.cols < previous.cols && terminal.rows < previous.rows &&
        pyodide.runPython("browser_app.size.width") === terminal.cols &&
        pyodide.runPython("browser_app.size.height") === terminal.rows;
    }, cells, { timeout: 10000 });
    t.diagnostic("Resize passed");

    await keyboard.press("Control+q");
    await page.waitForFunction(() =>
      document.querySelector("#status").textContent.startsWith("App stopped"),
    null, { timeout: 10000 });
    assert.equal(await python(page, "browser_app._runtime is None"), true);
    assert.equal(await python(page, "browser_driver._parser_task is None"), true);
    assert.equal(await python(page, "len(forbidden_operations)"), 0);
    assert.equal(await page.locator("#error").isVisible(), false);
    assert.deepEqual(errors, []);
    t.diagnostic("Shutdown and no-thread/socket guards passed");
    failed = false;
  } finally {
    try {
      await writeFile(path.join(artifacts, "browser-errors.json"), JSON.stringify(errors, null, 2));
      if (failed) {
        try {
          await page.screenshot({ path: path.join(artifacts, "failure.png"), fullPage: true });
        } catch (error) {
          t.diagnostic(`Could not capture screenshot: ${error}`);
        }
      }
      try {
        await context.tracing.stop(failed ? { path: path.join(artifacts, "trace.zip") } : {});
      } catch (error) {
        t.diagnostic(`Could not save trace: ${error}`);
      }
    } finally {
      await context.close();
    }
  }
});
