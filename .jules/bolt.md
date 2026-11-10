## 2024-06-25 - Replace subprocess with direct module imports
**Learning:** Python application used subprocesses frequently for small validation logic, which accrued massive startup overhead (e.g., hundreds of milliseconds per validation).
**Action:** When a Python script exposes programmatic functions like `stale_detector.py` and `output_validator.py`, directly import the module and invoke the functions to save on Python interpreter instantiation overhead. Avoid altering APIs when they aren't clean, such as `auto_rework.py`, which relies on `sys.exit` and stdout.
