# Browser diagnostics workflow

Date: 2026-05-14

This workflow keeps ParserRIba's runtime stable: Camoufox remains the parser
browser, while Chrome and MCP tools are used only for inspection.

## What each tool is for

- Camoufox visual smoke: the main field check for Pyaterochka. Use it with RU
  proxy, GeoIP, persistent profile, loaded images and manual captcha solving.
- Chrome DevTools MCP: inspect Chrome network, console, DOM and performance when
  a page visually opens but ParserRIba still gets empty products.
- Playwright MCP: quick browser observation and selector checks on simpler pages.
- Chrome scraping extensions: optional manual selector/API reconnaissance in a
  separate Chrome profile. Do not ship them with ParserRIba.

## Data that may go into the project

- CSS selectors;
- public catalog/API endpoint shapes;
- HTTP status codes;
- response shape notes such as empty `products` or missing selected store;
- non-secret screenshots/HTML saved by smoke tests.

## Data that must not go into the project

- `.env` values;
- proxy credentials;
- cookies, auth headers and captcha tokens;
- GitHub tokens or browser profile data;
- Chrome extension exports containing private sessions.

## Pyaterochka investigation flow

1. Run visual smoke:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_pyaterochka_visual.ps1
```

2. Solve captcha manually in Camoufox. Press Enter only after product cards are
   visible, not just after the category title appears.
3. Open `data\pyaterochka_camoufox_smoke.md`.
4. Check `Product API Diagnostics`:
   - if `Products list empty` or `Products response null` is true, product data
     did not reach the page;
   - if `Selected store detected` or `Address detected` is false, investigate
     region/store selection first;
   - if `Empty product payload samples` exists, compare those API URLs in Chrome
     DevTools MCP.
5. Only after the cause is clear, update `knowledge_base/pyaterochka.md` or the
   Camoufox smoke behavior. Do not add Chrome as a second parser runtime.

## Local Codex MCP setup

Expected local tools:

- `filesystem`
- `git`
- `sqlite`
- `context7`
- `playwright`
- `chrome-devtools`
- `memory`

Check inside Codex:

```text
/mcp
```

GitHub MCP remains disabled until a separate token is created. Do not store that
token in the repository.

Chrome DevTools MCP should be configured with privacy flags:

- `--no-usage-statistics`
- `--no-performance-crux`
- `--redactNetworkHeaders=true`
