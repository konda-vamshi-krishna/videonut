## 2024-10-29 - Pre-compiling Regex in script_normalizer.py
**Learning:** `script_normalizer.py` heavily uses regex for markdown stripping, applying many `re.sub()` calls for every line in a voice script. Currently it calls `re.sub` directly with raw strings, causing regex to compile on every call.
**Action:** Pre-compile these regular expressions to optimize `strip_markdown` function.
