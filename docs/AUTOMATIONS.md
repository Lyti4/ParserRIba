# ParserRIba Automations

Date: 2026-05-15

## Purpose

This file describes how to continue ParserRIba from a new chat or recurring
automation without relying on hidden chat history.

## Start Prompt For A New Chat

Use this prompt when starting a fresh Codex chat:

```text
Continue ParserRIba in C:\tmp\ParserRIba-clean. First read AGENTS.md,
docs/PROJECT_STATE.md, docs/NEXT_STEPS.md, docs/ROADMAP_V1.md,
docs/TOOLS_POLICY.md,
docs/AUTOMATIONS.md and docs/ARCHITECTURE_STEWARD.md. Then run git status, run
the relevant tests, and continue the active plan without adding paid services
or committing secrets.
```

## Safe Automation Prompt

Use this prompt for a heartbeat or recurring task:

```text
Continue ParserRIba in C:\tmp\ParserRIba-clean. Read AGENTS.md,
docs/PROJECT_STATE.md, docs/NEXT_STEPS.md, docs/ROADMAP_V1.md and
docs/TOOLS_POLICY.md. Check git status. Run tests if source files changed.
Continue the active Pyaterochka data interception and API-first extraction
plan. Do not add paid services, cloud LLMs, captcha-solving services or browser
APIs without explicit approval. Do not commit .env, proxy credentials, cookies,
captcha tokens, profiles, logs, data, build output, mmdb files or
__pycache__.
```

## Useful Automation Types

- Hourly or manual continuation after model/tool limits refresh.
- Daily project health check: tests, compileall and architecture check.
- Smoke report triage after the user runs visual Pyaterochka mode manually.
- Git cleanliness check before commits.
- Documentation sync after large changes.

## Commands

Health check:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q main.py models parsers policies strategies utils scripts tests
.\.venv\Scripts\python.exe scripts\architecture_check.py
git status --short
```

Git safety check:

```powershell
git status --short
git ls-files | rg "__pycache__|\.pyc$|^logs/|^build/|^dist/|GeoLite2|\.env$|^data/"
```

## Current Automation Policy

- Prefer continuing from repository docs, not from chat memory.
- Prefer source changes plus tests over broad rewrites.
- Keep generated runtime data local and ignored.
- Push only when the user asks or when an automation explicitly says to commit
  and push.
- If Context7 quota is exceeded, continue with local code and official docs only
  when needed.
