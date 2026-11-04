## 2026-11-04 - Subprocess overhead for python tools
**Learning:** Calling python scripts using `subprocess.run([sys.executable, ...])` within the orchestrator loop introduces significant process-creation and python interpreter startup overhead (especially bad on Windows).
**Action:** Always prefer direct imports of functions from the internal tool modules instead of running them as external scripts via `subprocess.run`.
