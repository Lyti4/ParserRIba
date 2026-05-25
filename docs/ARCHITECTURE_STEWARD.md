# ParserRIba Architecture Steward

Date: 2026-05-14

## Purpose

The architecture steward is a local Codex workflow for keeping ParserRIba stable
while the project moves from smoke scripts to a distributable parser app.

The main architecture and delivery direction for the current stage is tracked
in `docs/ROADMAP_V1.md`. Use the steward for health checks and refactor
pressure, and use the roadmap for product-shape decisions.

It is not part of the user-facing program, does not run in the background, and
does not call paid scraping, captcha, LLM, or cloud services. Its job is to
review the repository before large changes and before release builds.

## Steward Responsibilities

- Keep one canonical parser contract and flag drift between old parser layers.
- Keep Camoufox setup centralized in `utils.camoufox_launcher`.
- Keep store-specific URLs, selectors, headers, and strategy notes in
  `knowledge_base/`.
- Keep secrets, proxy credentials, browser profiles, logs, build output, and
  binary caches out of Git.
- Keep diagnostic scripts useful, but stop them from becoming the permanent
  runtime architecture.
- Track when a file is a refactor candidate, a removal candidate, or a current
  runtime dependency.

## Regular Checks

Run the fast checks before large parser changes:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q main.py models parsers policies strategies utils scripts tests
.\.venv\Scripts\python.exe scripts\architecture_check.py
```

Before a release candidate, also run:

```powershell
git status --short
git ls-files | rg "__pycache__|\.pyc$|^logs/|^build/|^dist/|GeoLite2|\.env$"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1 -Clean
dist\ParserRIba\ParserRIba.exe --check-env
```

## Current Refactor Candidates

- `utils/session_manager.py`: legacy experimental session code. Replace with a
  smaller SessionPool that uses loguru, async-safe state, proxy affinity,
  cooldowns, and health scoring.
- `parsers/base.py` is the active parser contract.
- `parsers/base_parser.py` plus old non-Pyaterochka store parsers are legacy
  quarantine code, not active runtime dependencies.
  Choose one canonical parser contract before stabilizing more stores.
- `parsers/playwright_parser.py`: keep only if it becomes a real fallback.
- `scripts/smoke_pyaterochka_camoufox.py`: useful but too large. Split later
  into network diagnostics, card extraction, attempt orchestration, and report
  writing.

These files should not be deleted just because they are listed here. First add
tests or a compatibility path, then remove or archive the old behavior.

## Supporting Plans

- `docs/ROADMAP_V1.md`: primary architecture and delivery roadmap.
- `docs/PROJECT_FILE_FLOW_MAP.md`: generated physical map of Python file
  dependencies, launch paths, runtime circumstances and cleanup candidates.
- `docs/PLATFORM_FOUNDATION.md`: platform primitives and refactor base.
- `docs/DATA_INTERCEPTION_PLAN.md`: safe interception and API-first data path.

## Cleanliness Rules

- Remove tracked generated files from the Git index, not from the user's local
  machine, unless the user explicitly asks to delete them.
- Never commit `.env`, proxy strings, cookies, profile data, captcha tokens,
  `GeoLite2-City.mmdb`, `profiles/`, `data/`, `logs/`, `build/`, `dist/`,
  `__pycache__/`, or `.pyc` files.
- Treat Chrome DevTools MCP and Playwright MCP as diagnostics tools. ParserRIba
  runtime remains Python + Camoufox.

## Local Skill Roadmap

Created locally in `C:\Users\Дима\.codex\skills`:

1. `parserriba-architecture-steward`: repo health, drift checks, cleanup
   candidates, release gates.
2. `parserriba-parser-contract-check`: parser API, async behavior, KB usage,
   Pydantic v2 and Camoufox constraints.
3. `parserriba-camoufox-smoke-diagnostics`: guided reading of Pyaterochka smoke
   and API discovery reports.
4. `parserriba-proxy-diagnostics`: proxy preflight, HTTP 407/429/5xx, browser
   external IP, traffic-risk and route-stability triage.
5. `parserriba-site-error-diagnostics`: unified `Site Error Tracking`,
   `browser_observations`, MCP console/network observations, challenge,
   product API and selector-vs-runtime triage.

Use the architecture steward for broad repo health, parser contract check before
parser refactors, smoke diagnostics after visual/API discovery runs, and proxy
diagnostics whenever an attempt might be failing because of traffic, auth,
rate-limit, route instability, or proxy/session drift. Use site error
diagnostics when a report already has multiple error families and the next
action is unclear.
