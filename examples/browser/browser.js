const status = document.querySelector("#status");
const errorBox = document.querySelector("#error");
document.querySelector("#reload").addEventListener("click", () => location.reload());
let terminal;
let fit;
let ready = false;
let input;
let resize;
let observer;
const subscriptions = [];
const proxies = [];

try {
  terminal = new Terminal({
    cursorBlink: true,
    fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace",
    fontSize: 14,
    theme: { background: "#0c0e14" },
    allowProposedApi: false,
  });
  fit = new FitAddon.FitAddon();
  terminal.loadAddon(fit);
  terminal.open(document.querySelector("#terminal"));
  fit.fit();
  observer = new ResizeObserver(() => fit.fit());
  observer.observe(document.querySelector("#terminal"));

  const { loadPyodide } = await import(
    "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs"
  );
  const pyodide = await loadPyodide();
  // Expose the interpreter and terminal for inspection in browser devtools.
  window.anytextDemo = { pyodide, terminal };
  status.textContent = "Installing Anytext…";
  await pyodide.loadPackage("micropip");
  const manifestResponse = await fetch("wheel.json", { cache: "no-store" });
  if (!manifestResponse.ok) throw new Error("Could not load the demo package manifest");
  const manifest = await manifestResponse.json();
  pyodide.globals.set("wheel_url", new URL(manifest.wheel, location.href).href);
  await pyodide.runPythonAsync("import micropip; await micropip.install(wheel_url)");
  pyodide.globals.set("terminal_write", (data) => terminal.write(data));
  pyodide.globals.set("terminal_cols", terminal.cols);
  pyodide.globals.set("terminal_rows", terminal.rows);
  pyodide.globals.set("browser_ready", () => {
    ready = true;
    resize(terminal.cols, terminal.rows);
    status.textContent = "Running · Python threads disabled";
    terminal.focus();
  });
  const sourceResponse = await fetch("app.py", { cache: "no-store" });
  if (!sourceResponse.ok) throw new Error("Could not load app.py");
  pyodide.runPython(await sourceResponse.text());
  input = pyodide.globals.get("browser_input");
  resize = pyodide.globals.get("browser_resize");
  proxies.push(input, resize);
  subscriptions.push(terminal.onData((data) => { if (ready) input(data); }));
  subscriptions.push(terminal.onResize(({ cols, rows }) => {
    if (ready) resize(cols, rows);
  }));
  await pyodide.runPythonAsync(
    "await browser_app.run_async(size=(terminal_cols, terminal_rows))"
  );
  status.textContent = "App stopped · Reload to start again";
} catch (error) {
  status.textContent = "Could not start Anytext";
  errorBox.textContent = String(error);
  errorBox.hidden = false;
  console.error(error);
} finally {
  ready = false;
  for (const subscription of subscriptions) subscription.dispose();
  for (const proxy of proxies) proxy.destroy();
  observer?.disconnect();
}
