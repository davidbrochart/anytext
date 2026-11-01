// NODE_PATH=/path/to/node_modules node tools/check_pyodide.cjs /path/to/site-packages
// Dependencies in site-packages must be pure Python (as Anytext's core deps are).
const { loadPyodide } = require("pyodide");
const fs = require("node:fs");
const path = require("node:path");

(async () => {
  if (!process.argv[2]) {
    throw new Error("Pass the Python environment's site-packages directory");
  }
  const repo = path.resolve(__dirname, "..");
  const pyodide = await loadPyodide();
  for (const [target, root] of [
    ["/repo", repo],
    ["/deps", path.resolve(process.argv[2])],
  ]) {
    pyodide.FS.mkdir(target);
    pyodide.FS.mount(pyodide.FS.filesystems.NODEFS, { root }, target);
  }
  await pyodide.runPythonAsync(`
import sys
sys.path[:0] = ['/repo/src', '/deps']
print('Pyodide:', sys.version.split()[0], sys.platform)
`);
  const smoke = fs.readFileSync(path.join(repo, "tests/wasm/smoke.py"), "utf8");
  await pyodide.runPythonAsync(smoke + "\nawait main()\n");
  console.log("PASS: thread-free Pyodide input, output, widgets, delivery and shutdown");
  // Pyodide's host event-loop machinery can otherwise keep Node running.
  process.exit(0);
})().catch((error) => {
  console.error(String(error));
  process.exit(1);
});
