## 2024-10-30 - Initial entry
**Learning:** This is a CLI tool, not a traditional web frontend.
**Action:** Focus on improving terminal output formatting, script descriptions, or setup instructions instead of React/HTML components.

## 2024-10-30 - Spinner clearing UX
**Learning:** Basic '\r' for terminal progress bars doesn't fully clear longer previous text lines on updates or completion, leaving text artifacts.
**Action:** Use readline.clearLine and readline.cursorTo when process.stdout.isTTY is true, or output spaces/ANSI escape codes to properly clear progress messages.
