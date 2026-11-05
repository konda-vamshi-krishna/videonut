## 2024-11-05 - Avoid Subprocess Overhead for Internal Python Scripts
**Learning:** Invoking internal python scripts using `subprocess.run(sys.executable, ...)` in `_video_nut/workflow_orchestrator.py` introduced significant python interpreter startup overhead for every pipeline gate/check. These are internal modules, so they can be safely imported and run in-process.
**Action:** Replace `subprocess.run` calls to internal python modules with direct `import` and function calls, capturing exceptions appropriately.
