## 2024-11-02 - Eliminate Python interpreter startup overhead for internal validators
**Learning:** Using `subprocess.run` to call internal Python scripts adds significant overhead (~30-50ms per call) because it starts a new Python interpreter each time. In a workflow orchestrator that runs many gates and validations, this adds up to noticeable delay.
**Action:** Always import and call internal Python functions directly instead of using `subprocess.run` unless process isolation is strictly necessary.
