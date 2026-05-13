# External research notes

Date: 2026-05-12

## Sources checked

- Chrome DevTools MCP: https://github.com/ChromeDevTools/chrome-devtools-mcp
- daijro repositories: https://github.com/daijro
- Crawlee: https://github.com/apify/crawlee
- BrowserAct skills ecosystem: https://github.com/browser-act/skills

## What is useful for ParserRIba

### Chrome DevTools MCP

Useful idea: browser observability. The project exposes Chrome DevTools-like
capabilities for agents: screenshots, network inspection, console messages and
performance traces. We should not replace Camoufox with Chrome, but the same
diagnostic shape is useful:

- save screenshot;
- save HTML;
- capture final URL;
- capture HTTP status;
- capture console/network summary later.

Already implemented:

- screenshot;
- HTML dump;
- status/final URL;
- Markdown/JSON smoke report.
- network response summary for the Pyaterochka smoke test;
- focused catalog/API response samples in the smoke report.

### daijro repositories

Useful projects:

- Camoufox: keep as the main browser layer.
- BrowserForge: keep as fingerprint/fingerprint-data dependency.
- hrequests: postpone. ParserRIba is Python, but Pyaterochka currently needs a
  real browser path more than another HTTP client.
- geoip-all-in-one: do not copy code because of licensing considerations. Keep
  local `GeoLite2-City.mmdb` support.

Already implemented:

- `camoufox[geoip]`;
- RU locale default;
- GeoIP database discovery;
- local Camoufox executable;
- proxy rotation for attempts.

Next:

- field-test with real RU proxy pool;
- keep BrowserForge generation inside Camoufox and expose only safe constraints:
  OS, locale, screen, window, WebRTC, WebGL, image loading and humanize.
- consider bundled Camoufox fingerprint presets only after smoke reports show a
  stable failure pattern and only when the installed Camoufox binary supports it well.

### Crawlee

Useful idea: crawler architecture, retries, sessions, proxy rotation and
separate request-level reporting. Crawlee itself is Node.js/TypeScript, so we
should not port it directly into this Python project.

Already implemented:

- attempt count;
- proxy pool;
- per-attempt report.

Next:

- add a small Python session report model for browser attempts;
- add retry reason categories.

### BrowserAct skills

Useful idea: reusable task-specific browser workflows. For ParserRIba this maps
to small scripts and documented commands, not to integrating a paid browser or
agent browser.

Already implemented:

- dedicated Pyaterochka visual smoke command.

Next:

- add a simple PowerShell helper for manual captcha inspection.

## Captcha decision

Do not automate captcha solving or integrate anti-captcha services. It would
turn the project from diagnostics/parsing into bypass automation, and the user
explicitly asked not to add paid/cloud services without approval.

Supported path:

- open visible Camoufox;
- allow images;
- keep browser open;
- let the user solve captcha manually;
- continue collecting diagnostics after product cards are visible;
- reuse a persistent local Camoufox profile so solved sessions can survive the next run.

Current follow-up:

- if the catalog shell opens but product cards remain empty, inspect the
  Catalog/API samples section in `data/pyaterochka_camoufox_smoke.md`;
- verify whether the saved session, address/store selection, or a product API
  challenge is still preventing products from loading.

Command:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_pyaterochka_visual.ps1
```
