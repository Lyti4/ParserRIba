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
- `utils.interception` now provides the store-neutral interception event shape:
  route type, payload kind, response size, product samples, schema hints and
  replay-candidate markers.
- `utils.interception_profiles` now contains store-specific route classifiers.
  Pyaterochka API classification is isolated there instead of being embedded in
  network capture code.
- `utils.interception_archive` writes compact safe JSON archives under
  `data/interception/` for later extractor work.
- `utils.api_first_extractor` now turns safe product samples from intercepted
  responses into deduplicated API-first candidates with readiness diagnostics.
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

1. Move interception profile values into `knowledge_base/` after the KB loader
   is cleaned up.
2. Add replay-candidate diagnostics only after confirming no secret headers are
   needed. Do not replay protected requests automatically.
3. Feed successful product payloads into the final `Product` model once real
   Pyaterochka product links and price fields are confirmed from reports.
4. Keep DOM/card extraction as a fallback after the API-first path is stable.

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
