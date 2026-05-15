# ParserRIba

ParserRIba is a Windows-focused Python project for parsing fish and seafood
prices from Russian retail stores.

The current development focus is Pyaterochka: Camoufox launch stability, proxy
diagnostics, anti-bot/challenge visibility, safe network interception and
API-first product extraction.

This repository is not yet a polished end-user release. It is a working parser
lab moving toward a downloadable desktop app.

## Current Status

What is already in place:

- Python 3.11 local development flow on Windows.
- Camoufox-based visual smoke test for Pyaterochka.
- Persistent Camoufox profile support for Pyaterochka.
- RU proxy support through `.env`, including proxy masking in reports.
- GeoIP support through local `GeoLite2-City.mmdb`.
- Manual captcha workflow for visual investigation.
- Passive API discovery for Pyaterochka catalog/network responses.
- Safe network diagnostics with masked URLs and no cookies/auth headers saved.
- Proxy health classification and local proxy history in SQLite.
- Site error tracking for browser, proxy, network, challenge and product API
  problems.
- Store-neutral interception events with route type, schema hints, product
  samples and replay-candidate markers.
- API-first product candidate diagnostics from safe intercepted samples.
- Architecture/project-state docs for future chats and automations.

Known limitations:

- Pyaterochka can still show rotate-image captcha/challenge pages.
- Product API extraction now has a safe candidate layer, but it is not yet the
  main parser path until real Pyaterochka payload fields are confirmed.
- Other store parsers still need cleanup and contract alignment.
- GUI, installer, backend, Postgres and dashboard are planned later.

## Project Layout

```text
knowledge_base/                 Store URLs, selectors and strategy notes
models/                         Pydantic data models
parsers/                        Store parser implementations and legacy parser layers
policies/                       Error/action policy engine
scripts/                        Smoke, discovery, build and architecture scripts
strategies/                     Scroll, lazy-load, pagination and captcha helpers
tests/                          Unit and smoke tests
utils/                          Shared runtime and diagnostics helpers
docs/                           Project state, plans, release and diagnostics docs
```

Important current modules:

- `utils.camoufox_launcher`: shared Camoufox launch options.
- `utils.network_capture`: safe response/failure capture.
- `utils.network_diagnostics`: network summary and proxy health.
- `utils.interception`: structured API/network interception events.
- `utils.api_first_extractor`: deduplicated product candidates from safe
  intercepted samples.
- `utils.proxy_history`: local SQLite proxy outcome history.
- `utils.site_error_tracking`: unified report error events.
- `utils.run_context`, `utils.session_pool`, `utils.rate_profile`: platform
  foundation for attempts, sessions and conservative timing.

## Requirements

- Windows 10/11
- Python 3.11 recommended
- Git
- Node.js only for optional MCP/dev tooling
- Working RU proxy recommended for Pyaterochka investigation

Python is expected at:

```powershell
C:\Python311\python.exe
```

## Setup

From the repository root:

```powershell
C:\Python311\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Optional Camoufox browser fetch:

```powershell
.\.venv\Scripts\python.exe -m camoufox fetch
```

## Environment

Create a local `.env` file if you need proxy/GeoIP settings. Do not commit it.

Useful variables:

```dotenv
PARSER_PROXY=http://user:password@host:port
PARSER_PROXIES=http://user:password@host1:port;http://user:password@host2:port
PARSER_GEOIP=true
```

Generated local files are intentionally ignored:

- `.env`
- `data/`
- `profiles/`
- `logs/`
- `GeoLite2-*.mmdb`
- `build/`
- `dist/`
- `__pycache__/`

## Basic Commands

Check environment:

```powershell
.\.venv\Scripts\python.exe main.py --check-env
```

List configured stores:

```powershell
.\.venv\Scripts\python.exe main.py --list-stores
```

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Run architecture check:

```powershell
.\.venv\Scripts\python.exe scripts\architecture_check.py
```

Compile check:

```powershell
.\.venv\Scripts\python.exe -m compileall -q main.py models parsers policies strategies utils scripts tests
```

## Pyaterochka Visual Smoke

Use this when checking the real browser flow, captcha behavior and product
visibility:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_pyaterochka_visual.ps1
```

If a captcha appears, solve it manually in the Camoufox window. Press Enter in
PowerShell only after the catalog/product cards are visible.

Reports are written to:

```text
data/pyaterochka_camoufox_smoke.json
data/pyaterochka_camoufox_smoke.md
```

Useful report sections:

- `Run Context`
- `Network`
- `Proxy Diagnostics`
- `Proxy History`
- `Site Error Tracking`
- `Product API Diagnostics`
- `Sample Products`

## Pyaterochka API Discovery

Use passive discovery after the browser is open and the challenge is solved:

```powershell
.\.venv\Scripts\python.exe scripts\discover_pyaterochka_api.py --listen-seconds 180
```

Reports are written to:

```text
data/pyaterochka_api_discovery.json
data/pyaterochka_api_discovery.md
```

The discovery report includes an `Interception` section with:

- route counts;
- product payload candidates;
- schema hints;
- replay-candidate markers.

It also includes an `API-first Extraction` section. This tells us how many safe
product candidates were found, how many already have the fields needed for the
final product model, and which fields are still missing.

Replay candidates are diagnostics only. The project does not automatically
replay protected requests until the safe API path is understood.

## Project Memory For New Chats

The repository now contains project-state files so new chats and automations can
continue without hidden chat history.

Read these first:

```text
AGENTS.md
docs/PROJECT_STATE.md
docs/NEXT_STEPS.md
docs/AUTOMATIONS.md
docs/ARCHITECTURE_STEWARD.md
docs/DECISIONS.md
```

Suggested prompt for a new Codex chat:

```text
Continue ParserRIba in C:\tmp\ParserRIba-clean. First read AGENTS.md,
docs/PROJECT_STATE.md, docs/NEXT_STEPS.md, docs/AUTOMATIONS.md and
docs/ARCHITECTURE_STEWARD.md. Then run git status, run the relevant tests, and
continue the active plan without adding paid services or committing secrets.
```

## Local Codex Skills

Local project skills are stored under:

```text
C:\Users\Дима\.codex\skills
```

Current project skills:

- `parserriba-architecture-steward`
- `parserriba-parser-contract-check`
- `parserriba-camoufox-smoke-diagnostics`
- `parserriba-proxy-diagnostics`
- `parserriba-site-error-diagnostics`

They are helper instructions for Codex. They are not runtime dependencies for
end users.

## MCP Tooling

Configured local MCP servers include:

- `filesystem`
- `git`
- `sqlite`
- `context7`
- `playwright`
- `chrome-devtools`
- `memory`
- `sequential-thinking`

Chrome DevTools MCP and Playwright MCP are diagnostics tools only. ParserRIba
runtime remains Python + Camoufox.

## Development Priorities

Current order:

1. Stabilize Pyaterochka visual smoke and API discovery.
2. Move Pyaterochka route/API detection from the temporary store profile into
   the KB-backed classifier after KB loader cleanup.
3. Keep saving compact safe interception reports.
4. Promote API-first candidates into the final Pyaterochka product mapper after
   real payload fields are confirmed.
5. Keep DOM/card extraction as fallback.
6. Add local SQLite product and price history.
7. Add normalization and deduplication.
8. Move to FastAPI/Postgres/workers/dashboard only after useful data is stable.

## Safety Rules

- Do not commit `.env`, proxy credentials, cookies, auth headers, captcha
  tokens, browser profiles, generated reports or local databases.
- Do not add paid scraping APIs, captcha-solving services, hosted LLMs or cloud
  services without explicit approval.
- Do not treat Chrome/Playwright MCP as the production parser runtime.
- Keep store-specific URLs and selectors in `knowledge_base/`.
- Keep tests green before pushing.

## Build Notes

Portable Windows build support exists, but public release work should wait until
the parser path is stable:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1 -Clean
```

Release planning lives in:

- `docs/DISTRIBUTION_PLAN.md`
- `docs/INSTALLER_ROADMAP.md`
- `docs/RELEASE_CHECKLIST.md`
