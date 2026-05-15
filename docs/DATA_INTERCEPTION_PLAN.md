# ParserRIba Data Interception Plan

Date: 2026-05-15

## Goal

Turn the current passive Pyaterochka network discovery into a reusable data
interception block. It should capture only safe catalog/API diagnostics and
product payload candidates, never cookies, auth headers, proxy credentials or
captcha tokens.

## Current Base

- `utils.network_capture` already records safe response/failure events.
- `utils.api_discovery` already detects likely product JSON payloads.
- `utils.site_error_tracking` normalizes browser, proxy, network, challenge,
  product API and discovery errors into one report block.
- `utils.site_error_tracking.build_browser_observations` accepts normalized
  Playwright/Chrome DevTools MCP console and network observations, so lab data
  can be merged into the same error report shape.
- `scripts.discover_pyaterochka_api` already opens Camoufox and passively
  listens to responses after manual captcha solving.
- `utils.proxy_history` now records whether the proxy route was healthy enough
  for the discovery run.

## Implementation Order

1. Add `utils.interception` with a store-neutral interception result model:
   route type, method, status, masked URL, content type, response size, payload
   preview, candidate product count and sample products.
2. Move Pyaterochka-specific URL/API detection into a KB-backed or store-profile
   classifier instead of keeping it only in discovery helpers.
3. Save a compact `data/interception/*.json` report per run with safe samples.
4. Add schema hints for captured product payloads: id/name/price/image/link keys.
5. Add replay-candidate diagnostics only after confirming no secret headers are
   needed. Do not replay protected requests automatically.
6. Feed successful product payloads into API-first extraction, with DOM/card
   extraction as a fallback.

## Acceptance Rules

- No cookies, captcha tokens, authorization headers or proxy credentials are
  written to disk.
- Reports must explain whether failure is proxy health, challenge/session state,
  missing store/address or empty product payload.
- Error reports should use `utils.site_error_tracking` so Playwright/Chrome
  DevTools MCP observations can be merged later without changing report shape.
- MCP observations should enter reports as `browser_observations`, not as raw
  tool output. Keep URLs masked/sanitized and never store cookies or headers.
- All interception helpers must have unit tests with synthetic responses.
- Camoufox remains the runtime browser; Chrome DevTools MCP is only a lab tool.
