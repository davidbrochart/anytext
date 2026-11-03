const assert = require("node:assert/strict");
const { spawn } = require("node:child_process");
const { mkdir, readFile, unlink, writeFile } = require("node:fs/promises");
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
    [path.join(repo, "tools/serve_browser.py"), "--port", "0", "--base-path", "anytext"],
    { cwd: repo, stdio: ["ignore", "pipe", "pipe"] },
  );
  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error(`Server startup timed out:\n${serverLog}`)), 30000);
    function record(chunk) {
      serverLog += chunk.toString();
      const match = serverLog.match(/Open (http:\/\/127\.0\.0\.1:\d+\/\S*)/);
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
  assert.ok(baseURL.endsWith("/anytext/"), "Exercise a GitHub Pages project URL");
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

function waitForPython(page, expression, timeout = 10000) {
  return page.waitForFunction(
    (code) => window.anytextDemo.pyodide.runPython(code),
    expression,
    { timeout },
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

async function assertPaneBoxBorders(page) {
  await waitForPython(page, "browser_app.screen.query_one('#split-demo').second.first.region.height == browser_app.screen.query_one('#split-demo').second.first_size and browser_app.screen.query_one('#split-demo').second.second.region.height == browser_app.screen.query_one('#split-demo').second.second_size");
  const boxes = JSON.parse(await python(page,
    "json.dumps([list(browser_app.screen.query_one('#split-demo').second.first.region), list(browser_app.screen.query_one('#split-demo').second.second.region)])"));
  await page.waitForFunction((regions) => {
    const buffer = window.anytextDemo.terminal.buffer.active;
    return regions.every(([x, y, width, height]) => {
      const top = buffer.getLine(buffer.baseY + y);
      const bottom = buffer.getLine(buffer.baseY + y + height - 1);
      if (!top || !bottom) return false;
      if (top.getCell(x)?.getChars() !== "╭" || top.getCell(x + width - 1)?.getChars() !== "╮" ||
          bottom.getCell(x)?.getChars() !== "╰" || bottom.getCell(x + width - 1)?.getChars() !== "╯") return false;
      for (let column = x + 1; column < x + width - 1; column++) {
        if (top.getCell(column)?.getChars() !== "─" || bottom.getCell(column)?.getChars() !== "─") return false;
      }
      return true;
    });
  }, boxes);
}

async function dragStackedPaneToLimits(page) {
  const divider = JSON.parse(await python(page,
    "json.dumps(list(browser_app.screen.query_one('#split-demo').second.divider.region))"));
  const screen = await page.locator(".xterm-screen").boundingBox();
  const cells = await page.evaluate(() => ({cols: window.anytextDemo.terminal.cols, rows: window.anytextDemo.terminal.rows}));
  const x = screen.x + (divider[0] + divider[2] / 2) * screen.width / cells.cols;
  const y = screen.y + (divider[1] + 0.5) * screen.height / cells.rows;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x, screen.y + 0.5 * screen.height / cells.rows, {steps: 5});
  await waitForPython(page, "browser_app.screen.query_one('#split-demo').second.first_size == browser_app.screen.query_one('#split-demo').second.min_first");
  await assertPaneBoxBorders(page);
  await page.mouse.move(x, screen.y + (cells.rows - 1.5) * screen.height / cells.rows, {steps: 5});
  await waitForPython(page, "browser_app.screen.query_one('#split-demo').second.second_size == browser_app.screen.query_one('#split-demo').second.min_second");
  await assertPaneBoxBorders(page);
  await page.mouse.up();
  await waitForPython(page, "browser_app.mouse_captured is None");
}

test("The official demo runs in Pyodide without threads under a Pages project path", { timeout: 180000 }, async (t) => {
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
    assert.equal(await page.evaluate(() => window.anytextDemo.terminal.unicode.activeVersion), "11");

    await waitForPython(page, "isinstance(browser_app, DemoApp) and browser_app.current_mode == 'home'");
    await waitForTerminalText(page, "What is Anytext?");
    await waitForTerminalText(page, "🐍");
    await waitForTerminalText(page, "👇");
    const emojiCells = await page.evaluate(() => {
      const terminal = window.anytextDemo.terminal;
      const found = [];
      for (let y = 0; y < terminal.buffer.active.length; y++) {
        const line = terminal.buffer.active.getLine(y);
        for (let x = 0; x < terminal.cols; x++) {
          const cell = line.getCell(x);
          if (["🐍", "👇"].includes(cell.getChars())) {
            found.push({ text: cell.getChars(), width: cell.getWidth(),
              continuation: line.getCell(x + 1)?.getWidth() });
          }
        }
      }
      return found;
    });
    assert.deepEqual(new Set(emojiCells.map(cell => cell.text)), new Set(["🐍", "👇"]));
    const richWidths = JSON.parse(await python(page,
      "import json; from rich.cells import cell_len; json.dumps({c: cell_len(c) for c in ['🐍', '👇']})"));
    for (const cell of emojiCells) {
      assert.equal(cell.width, richWidths[cell.text], `${cell.text} must occupy the same cells in xterm and Rich`);
      assert.equal(cell.continuation, 0, "A wide emoji must reserve its second terminal cell");
    }
    t.diagnostic("Rendered demo emoji widths agree with Rich");
    const keyboard = page.locator(".xterm-helper-textarea");
    await keyboard.press("c");
    await waitForPython(page, "browser_app.screen.__class__.__name__ == 'CodeScreen'");
    assert.equal(await python(page, "'class HomeScreen' in browser_app.screen.code"), true);
    await keyboard.press("Escape");
    await waitForPython(page, "browser_app.screen.__class__.__name__ == 'HomeScreen'");
    t.diagnostic("Official Home screen and source-code viewer passed");

    await keyboard.press("w");
    await waitForPython(page, "browser_app.current_mode == 'widgets' and len(browser_app.screen.query('Buttons Button')) > 1");
    await python(page, "browser_app.screen.query_one('Buttons Button').focus(); None");
    await keyboard.press("Enter");
    await waitForTerminalText(page, "you pressed Default");
    await python(page, "list(browser_app.screen.query('Buttons Button'))[1].focus(); None");
    await waitForPython(page, "list(browser_app.screen.query('Buttons Button'))[1].has_focus");
    const button = JSON.parse(await python(page,
      "import json; json.dumps(list(list(browser_app.screen.query('Buttons Button'))[1].region))"));
    const screen = await page.locator(".xterm-screen").boundingBox();
    assert.ok(screen);
    const buttonCells = await page.evaluate(() => ({
      cols: window.anytextDemo.terminal.cols,
      rows: window.anytextDemo.terminal.rows,
    }));
    await page.mouse.click(
      screen.x + (button[0] + button[2] / 2) * screen.width / buttonCells.cols,
      screen.y + (button[1] + button[3] / 2) * screen.height / buttonCells.rows,
    );
    await waitForTerminalText(page, "you pressed Primary");
    await waitForPython(page, "len(browser_app.screen.query('#split-demo')) == 1");
    await python(page, "browser_app.clear_notifications(); browser_app.screen.query_one('#split-demo').scroll_visible(animate=False); None");
    await waitForPython(page, "browser_app.screen.query_one('#split-demo').region.y >= 0 and browser_app.screen.query_one('#split-demo').region.bottom < browser_app.size.height");
    const split = JSON.parse(await python(page,
      "json.dumps({'size': browser_app.screen.query_one('#split-demo').first_size, 'divider': list(browser_app.screen.query_one('#split-demo').divider.region)})"));
    const splitScreen = await page.locator(".xterm-screen").boundingBox();
    const splitCells = await page.evaluate(() => ({ cols: window.anytextDemo.terminal.cols, rows: window.anytextDemo.terminal.rows }));
    const splitX = splitScreen.x + (split.divider[0] + 0.5) * splitScreen.width / splitCells.cols;
    const splitY = splitScreen.y + (split.divider[1] + split.divider[3] / 2) * splitScreen.height / splitCells.rows;
    await page.mouse.move(splitX, splitY);
    await page.mouse.down();
    await page.mouse.move(splitX + 6 * splitScreen.width / splitCells.cols, splitY, { steps: 6 });
    await page.mouse.up();
    await waitForPython(page, `browser_app.screen.query_one('#split-demo').first_size == ${split.size + 6}`);
    await waitForPython(page, "browser_app.mouse_captured is None");
    const nestedSplit = JSON.parse(await python(page,
      "json.dumps({'size': browser_app.screen.query_one('#split-demo').second.first_size, 'divider': list(browser_app.screen.query_one('#split-demo').second.divider.region)})"));
    const nestedX = splitScreen.x + (nestedSplit.divider[0] + nestedSplit.divider[2] / 2) * splitScreen.width / splitCells.cols;
    const nestedY = splitScreen.y + (nestedSplit.divider[1] + 0.5) * splitScreen.height / splitCells.rows;
    await page.mouse.move(nestedX, nestedY);
    await page.mouse.down();
    await page.mouse.move(nestedX, nestedY + 2 * splitScreen.height / splitCells.rows, { steps: 4 });
    await page.mouse.up();
    await waitForPython(page, `browser_app.screen.query_one('#split-demo').second.first_size == ${nestedSplit.size + 2}`);
    await waitForPython(page, "browser_app.mouse_captured is None");
    await dragStackedPaneToLimits(page);
    t.diagnostic("Horizontal and nested vertical split-pane mouse dragging passed");
    await python(page, "browser_app.screen.query_one('#split-show-divider').focus(); None");
    await keyboard.press("Space");
    await waitForPython(page, "not browser_app.screen.query_one('#split-demo').show_divider and not browser_app.screen.query_one('#split-demo').second.show_divider");
    await python(page, "browser_app.screen.query_one('#split-demo').scroll_visible(animate=False); None");
    await waitForPython(page, "browser_app.screen.query_one('#split-demo').first.parent.region.right == browser_app.screen.query_one('#split-demo').second.parent.region.x");
    const hiddenSplit = JSON.parse(await python(page,
      "json.dumps({'size': browser_app.screen.query_one('#split-demo').first_size, 'divider': list(browser_app.screen.query_one('#split-demo').divider.region)})"));
    const hiddenX = splitScreen.x + (hiddenSplit.divider[0] + 0.5) * splitScreen.width / splitCells.cols;
    const hiddenY = splitScreen.y + (hiddenSplit.divider[1] + hiddenSplit.divider[3] / 2) * splitScreen.height / splitCells.rows;
    await page.mouse.move(hiddenX, hiddenY);
    await page.mouse.down();
    await page.mouse.move(hiddenX + 3 * splitScreen.width / splitCells.cols, hiddenY, { steps: 3 });
    await page.mouse.up();
    await waitForPython(page, `browser_app.screen.query_one('#split-demo').first_size == ${hiddenSplit.size + 3}`);
    await waitForPython(page, "browser_app.mouse_captured is None");
    assert.equal(await python(page, "browser_app.screen.query_one('#split-demo').second.first.parent.region.bottom == browser_app.screen.query_one('#split-demo').second.second.parent.region.y"), true);
    await dragStackedPaneToLimits(page);
    t.diagnostic("Visible and invisible pane borders survive dragging to both limits");
    t.diagnostic("Invisible zero-gap divider toggling and browser mouse dragging passed");
    await waitForPython(page, "len(browser_app.screen.query('Inputs Input')) > 0");
    await python(page, "browser_app.screen.query_one('Inputs Input').focus(); None");
    await waitForPython(page, "browser_app.screen.query_one('Inputs Input').has_focus");
    await keyboard.pressSequentially("hello browser");
    await waitForPython(page, "browser_app.screen.query_one('Inputs Input').value == 'hello browser'");
    await keyboard.press("Escape");
    await waitForPython(page, "browser_app.screen.focused is None");
    t.diagnostic("Official Widgets screen, typing, keyboard and mouse buttons passed");

    const [download] = await Promise.all([
      page.waitForEvent("download"),
      keyboard.press("Control+s"),
    ]);
    assert.ok(download.suggestedFilename().endsWith(".svg"));
    assert.ok((await readFile(await download.path(), "utf8")).includes("<svg"));
    t.diagnostic("SVG screenshot download passed");

    await keyboard.press("p");
    await waitForPython(page, "browser_app.current_mode == 'projects' and len(browser_app.screen.query('Project')) > 0");
    const projectURL = await python(page, "browser_app.screen.query_one('Project').project_info.url");
    await page.evaluate(() => {
      window.openedLinks = [];
      window.open = (...args) => { window.openedLinks.push(args); return null; };
    });
    await python(page, "browser_app.screen.query_one('Project').focus(); None");
    await keyboard.press("Enter");
    await page.waitForFunction(() => window.openedLinks.length === 1);
    assert.deepEqual(await page.evaluate(() => window.openedLinks[0]),
      [projectURL, "_blank", "noopener,noreferrer"]);
    t.diagnostic("Official Projects screen and browser links passed");

    await keyboard.press("g");
    await waitForPython(page, "browser_app.current_mode == 'game'");
    await keyboard.press("n");
    await waitForPython(page, "browser_app.screen.__class__.__name__ == 'GameDialogScreen'");
    await python(page, "browser_app.screen.query_one('#level').value = (3, 3); browser_app.screen.query_one('Button').focus(); None");
    await keyboard.press("Enter");
    await waitForPython(page, "browser_app.screen.__class__.__name__ == 'GameScreen' and browser_app.screen.query_one('Game').state == 'playing'", 30000);
    t.diagnostic("Official Game screen, setup and async shuffle passed");
    await keyboard.press("h");
    await waitForPython(page, "browser_app.current_mode == 'home'");

    const cells = await page.evaluate(() => ({
      cols: window.anytextDemo.terminal.cols,
      rows: window.anytextDemo.terminal.rows,
    }));
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
    const rightEdges = await page.evaluate(async (widths) => {
      const terminal = window.anytextDemo.terminal;
      terminal.resize(20, 4);
      const rows = ["🐍", "👇"].map(emoji => emoji + " ".repeat(19 - widths[emoji]) + "|");
      await new Promise(resolve => terminal.write("\x1b[?7l\x1b[2J\x1b[H" + rows.join("\r\n"), resolve));
      return rows.map((_, y) => terminal.buffer.active.getLine(terminal.buffer.active.baseY + y).getCell(19).getChars());
    }, richWidths);
    assert.deepEqual(rightEdges, ["|", "|"], "Emoji must not shift the right edge or scrollbar column");
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
