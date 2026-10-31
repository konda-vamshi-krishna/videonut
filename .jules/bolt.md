
## 2024-10-31 - Subprocess Overhead in Orchestrator
**Learning:** Python scripts executed via `subprocess.run` inside a loop incur a significant interpreter startup overhead (~30-100ms per call depending on system load) compared to direct function calls (~0.2ms). In `workflow_orchestrator.py`, calling validation scripts (`stale_detector.py`, `output_validator.py`, `audio_validator.py`) as subprocesses created a notable, repetitive bottleneck across the lifecycle of the video generation pipeline.
**Action:** When executing internal Python utility scripts within the same project ecosystem, favor direct imports and function calls over `subprocess.run` to eliminate repeated interpreter initialization delays, as long as module boundaries allow it without creating dangerous side effects.
