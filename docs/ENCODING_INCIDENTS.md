# Encoding Incidents

This file records why ParserRIba had repeated Cyrillic/mojibake failures and
how to avoid the same failure class in future work.

## Incident Classes

### Legacy Mojibake In Active Files

**Symptom:** tests, docs and runtime helpers contained text like
`\u0420\xa0\u0421\u2039\u0420\xb1\u0420\xb0` instead of readable Russian.

**Cause:** Russian text had already been decoded with the wrong Windows
codepage and then saved as valid UTF-8.

**Prevention:**

- Run `.\.venv\Scripts\python.exe scripts\encoding_guard.py --changed` after
  editing docs, tests, specs, launcher text or runtime text.
- Run `.\.venv\Scripts\python.exe scripts\encoding_guard.py --staged` before
  commit.
- Keep `scripts/encoding_guard_baseline.json` at zero active findings unless a
  reviewed compatibility reason exists.

### PowerShell Rendering Is Not Evidence

**Symptom:** terminal output showed `????` or mojibake, but it was unclear
whether the file or only the console display was broken.

**Cause:** PowerShell and the terminal can render or transcode Cyrillic
incorrectly, especially around heredocs and inline commands.

**Prevention:**

- Verify file bytes or use `unicode_escape` output before changing code.
- Prefer `.\.venv\Scripts\python.exe scripts\utf8_command.py -- <command>` for
  commands that may print Russian text.
- Treat terminal rendering as a preview, not as proof.

### Unsafe Shell Writes

**Symptom:** a script or heredoc write changed Russian text into `?` or
mojibake.

**Cause:** non-ASCII text crossed a shell boundary with an unreliable encoding.

**Prevention:**

- Use `apply_patch` for manual source edits.
- For mechanical rewrites, read and write files with explicit UTF-8.
- When a shell boundary cannot be avoided, use ASCII `\uXXXX` literals and
  verify the resulting file with `unicode_escape`.

### Missing Staged Gate

**Symptom:** advice existed in skills, but errors could still be committed.

**Cause:** skills are guidance; they do not block commits.

**Prevention:**

- Use the optional local pre-commit hooks in `.pre-commit-config.yaml`.
- The canonical manual equivalent is:

```powershell
.\.venv\Scripts\python.exe scripts\encoding_guard.py --staged
.\.venv\Scripts\python.exe scripts\architecture_check.py
```

### Intentional Compatibility Markers

**Symptom:** some mojibake-like strings remain in code on purpose.

**Cause:** ParserRIba still needs to recognize old saved data and dirty site
payloads.

**Prevention:**

- Do not normalize marker constants blindly.
- Mark intentional locations through encoding guard compatibility metadata.
- Runtime output must be readable Russian; dirty input aliases may stay only
  when documented.

## Standard Commands

```powershell
.\.venv\Scripts\python.exe scripts\encoding_guard.py --changed
.\.venv\Scripts\python.exe scripts\encoding_guard.py --staged
.\.venv\Scripts\python.exe scripts\encoding_guard.py --all
.\.venv\Scripts\python.exe scripts\encoding_normalization_dry_run.py --changed
.\.venv\Scripts\python.exe scripts\agent_ops_check.py --scope changed --with-tests
```
