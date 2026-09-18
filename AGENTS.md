# ParserRIba Agent Guide

You are working on ParserRIba in `C:\tmp\ParserRIba-clean`.

ParserRIba is developed and run local-first. Treat `C:\tmp\ParserRIba-clean`
as the authoritative working copy for code, launcher runs, profiles, local
SQLite, JSON/Excel artifacts and diagnostics. The GitHub repository is used for
commits, history, backup and review only; do not treat the remote repository as
the active runtime source.

Read these files first in any new chat or automation:

1. `AGENTS.md`
2. `docs/PROJECT_STATE.md`
3. `docs/NEXT_STEPS.md`
4. `docs/DECISIONS.md`
5. `docs/ROADMAP_V1.md`
6. `docs/TARGET_ARCHITECTURE.md`
7. `docs/PROJECT_STRUCTURE.md`
8. `docs/TOOLS_POLICY.md`
9. `docs/AUTOMATIONS.md`
10. `docs/ARCHITECTURE_STEWARD.md`
11. `docs/AGENT_WORKFLOW.md`

## Project Rules

- Python 3.10+, asyncio-first.
- The launcher is the canonical user-facing product path.
- Browser runtime is Camoufox through async Playwright-compatible APIs.
- Keep URLs, selectors and store rules in `knowledge_base/`.
- Use Pydantic v2 models and loguru logging.
- Use SQLite as the local v1 storage layer for profiles, sessions, product
  snapshots, report presets and future price history.
- Do not add paid services, cloud LLMs, captcha-solving services or external
  APIs without explicit user approval.
- Do not commit secrets, `.env`, proxy credentials, browser profiles, cookies,
  captcha tokens, `GeoLite2-City.mmdb`, logs, `data/`, `dist/`, `build/`,
  `__pycache__/` or `.pyc`.

## Hard Constraints

- Do not call `.get()` on Pydantic model instances. Use attributes,
  `getattr(...)`, or `model_dump(...)`.
- Do not call `.close()` on `AsyncCamoufox` / `Camoufox`. Use `async with` or
  `__aexit__`.
- Do not use `time.sleep()`. Use `asyncio.sleep()` or browser wait APIs.
- Do not use `print()` for logs in runtime code. Use loguru.
- Keep new focused Python modules below 300 lines when practical.
- For orchestration entrypoints and large tests, up to roughly 450 lines is
  acceptable if the file still has one clear responsibility.
- After editing Russian/Cyrillic UI text, docs or tests, run
  `.\.venv\Scripts\python.exe scripts\encoding_guard.py --changed` before
  committing.
- Before committing Cyrillic or encoding-related changes, run
  `.\.venv\Scripts\python.exe scripts\encoding_guard.py --staged`. Optional
  local pre-commit hooks are defined in `.pre-commit-config.yaml`.
- When PowerShell output may contain Cyrillic, do not trust terminal rendering
  alone. Prefer `.\.venv\Scripts\python.exe scripts\utf8_command.py -- <command>`
  to save a UTF-8 log under ignored `logs/agent_utf8/` and print only an
  ASCII-safe preview.
- For recurring encoding incidents and prevention rules, read
  `docs/ENCODING_INCIDENTS.md`.
- For symbol-level code navigation, references, rename/refactor planning and
  large-file edits, prefer Serena MCP tools before reading whole Python files.
  Serena is dev tooling only and must not become ParserRIba runtime code.
- For agent workflow, skill routing, guard selection, subagent use and handoff
  discipline, use `docs/AGENT_WORKFLOW.md`.

## Current Focus

The current product direction is launcher-first. ParserRIba is being organized
as a local desktop program with separate cores for browser/discovery/catalog,
products, filters, reports, storage and store profiles.

Canonical user flow:

`Исследование -> Каталог -> Товары -> Отчёт -> Профиль/История`

Canonical architecture:

`Launcher -> Task Orchestrator -> Browser/Discovery Core -> Store Adapter -> Product Core -> Filter Core -> Report Core -> Storage/Profile Core`

Current priorities:

1. Keep the launcher-first workflow as the canonical user path.
2. Keep Pyaterochka protected-store mechanics available through a store adapter.
3. Improve store-neutral discovery and catalog tree/profile storage.
4. Collect full product cards from explicitly selected catalog nodes.
5. Build dynamic filters and reports from collected product data.
6. Make `StoreProfile` the owner of catalog snapshots, selected nodes, product
   workspaces, filter presets, report-column presets, artifacts and future
   price history.

Pyaterochka is the first `runtime_ready` store adapter. Unknown or new sites
remain `discovery_only` until a real product adapter exists.

The old CLI/parser stack is not a product runtime. Do not fix legacy bugs for
their own sake. If useful behavior exists there, extract it into a target core
or store adapter with tests, switch active callers to the new contract, and
then remove obsolete source from the working tree. Git history is the archive.

## Development Discipline

- Use replacement discipline for new features: define the new contract, switch
  active callers to it, then remove/archive the replaced path or document the
  exact blocker.
- Keep all visible launcher text in clear Russian.
- Keep JSON as an internal artifact; the user works through the launcher,
  tables, filters, reports and profile/session panels.
- Use Superpowers/subagents for read-only audit, impact analysis and independent
  slices when that reduces risk. Close subagents after their result.
- Do not keep two active implementations with unclear priority.

## Validation

Run from `C:\tmp\ParserRIba-clean`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q models utils scripts tests stores launcher
.\.venv\Scripts\python.exe scripts\architecture_check.py
.\.venv\Scripts\python.exe scripts\run_desktop_launcher.py --smoke
```

Expected current state: tests pass, compile succeeds, architecture check has no
errors. Removed legacy code is available through git history, not a tracked
runtime folder.

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
at specs/016-protected-manual-gate/plan.md
<!-- SPECKIT END -->
