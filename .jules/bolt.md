
## 2024-11-06 - Replace Subprocess Calls with Direct Imports
**Learning:** Using `subprocess.run` to call simple python validation or detector scripts adds significant process startup overhead, creating bottlenecks when these scripts are invoked repeatedly in the workflow orchestrator. This codebase has a mix of scripts designed as CLIs and ones with clean programmatic APIs.
**Action:** When a Python helper script exposes a clean programmatic API (like `output_validator.py`, `stale_detector.py`, `audio_validator.py` and `auto_rework.py`), always opt for direct Python imports rather than `subprocess.run`. Ensure proper `sys.path` insertion and import management to handle directory structure. We achieved >90% reduction in execution time for these functions.
