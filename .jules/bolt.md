
## 2023-11-08 - Subprocess vs Direct Import Overhead
**Learning:** In Python orchestration scripts (`workflow_orchestrator.py`), repeatedly using `subprocess.run` to invoke internal python tools (like `output_validator.py` and `stale_detector.py`) incurs a massive performance penalty. Each subprocess call starts a whole new Python interpreter instance. Benchmark showed a 266x speedup by converting to direct function imports.
**Action:** Always prefer direct imports (using `__init__.py` in tool directories) over `subprocess.run` for internal CLI tools, as long as the tool has cleanly decoupled functions that can be imported without side-effects.
