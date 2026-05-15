# ParserRIba Project State

Date: 2026-05-15

## Current Summary

ParserRIba is a Windows-focused Python parser project moving from scripts to a
stable, distributable application. The active work is concentrated on
Pyaterochka because it has the hardest anti-bot and API discovery path.

The repository is now the source of truth for project state. New chats and
automations should begin by reading `AGENTS.md`, this file, `docs/NEXT_STEPS.md`
and `docs/AUTOMATIONS.md`.

## Environment

- Primary workspace: `C:\tmp\ParserRIba-clean`
- Python: `C:\Python311\python.exe`
- Virtual environment: `C:\tmp\ParserRIba-clean\.venv`
- Main branch: `main`
- Remote: `https://github.com/Lyti4/ParserRIba.git`
- Last pushed project-foundation commit: `b195402`

## What Works

- Python 3.11 environment and dependencies are installed locally.
- Camoufox launches for Pyaterochka visual smoke.
- Persistent profile, RU proxy, GeoIP, images-on visual mode and manual captcha
  workflow are supported.
- Visual smoke and passive API discovery write JSON/Markdown reports.
- Proxy credentials are masked in logs and reports.
- Proxy history is stored in `data/proxy_history.db` using proxy hash and mask,
  not raw credentials.
- Site error tracking groups challenge, proxy, network, product API, discovery
  and MCP-observation errors into one report block.
- Store-neutral interception events now include route type, payload kind,
  response size, schema hints, product samples and replay-candidate markers.
- API-first product candidate extraction now turns safe intercepted samples into
  deduplicated candidate records with readiness and missing-field diagnostics.
- Local architecture/check/diagnostics skills exist under
  `C:\Users\Дима\.codex\skills`.

## Current Limitations

- Pyaterochka still may show rotate-image captcha and challenge flows.
- Product API payload capture is not yet proven stable on a real successful run.
- API-first extraction is still a candidate layer, not the final Product mapper.
  It needs real Pyaterochka payloads before it becomes the main parser path.
- `scripts/smoke_pyaterochka_camoufox.py` remains too large and should be split
  later.
- Legacy parser layers still have warnings: duplicate base contracts, old
  `.close()` calls, hardcoded URLs and `print()` calls.
- Other stores are not yet stabilized to the new platform foundation.
- No GUI/dashboard/backend/database product storage yet.

## MCP Status

Configured MCP servers in `C:\Users\Дима\.codex\config.toml`:

- `filesystem`
- `git`
- `sqlite`
- `context7`
- `playwright`
- `chrome-devtools`
- `memory`
- `sequential-thinking`

`github` MCP is not enabled until a separate token is available. `postgres` MCP
is not enabled because the project is still using local SQLite diagnostics.

## Local Skills

- `parserriba-architecture-steward`
- `parserriba-parser-contract-check`
- `parserriba-camoufox-smoke-diagnostics`
- `parserriba-proxy-diagnostics`
- `parserriba-site-error-diagnostics`

Use these skills when their topic appears. They are project helpers, not runtime
dependencies for end users.

## Safety Notes

- Do not commit `.env`, proxy strings, cookies, captcha tokens, auth headers,
  browser profiles, generated reports, mmdb databases, logs or build output.
- Do not integrate paid browser APIs, paid captcha solving, cloud scraping or
  LLM services without explicit user approval.
- Treat Chrome DevTools MCP and Playwright MCP as diagnostics labs. Runtime
  remains Python + Camoufox.
