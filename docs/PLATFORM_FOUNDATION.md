# ParserRIba Platform Foundation

Date: 2026-05-14

## What Was Added

ParserRIba now has the first reusable platform objects:

- `utils.rate_profile.RateProfile`: conservative timing, retry and cooldown
  policy for protected stores.
- `utils.run_context.RunContext`: one parser run with stable `run_id`.
- `utils.run_context.AttemptContext`: one browser/proxy/category attempt.
- `utils.run_context.StoreState`: observed address/store/catalog state.
- `utils.run_context.DiagnosticEvent`: report-safe diagnostic event.
- `utils.session_pool.SessionPool`: local in-memory session pool with proxy
  affinity, health counters, quarantine and masked summaries.

These modules are intentionally not wired into every parser yet. They are the
safe base for the next refactor step.

## Wiring Status

- Passive Pyaterochka API discovery now includes `RunContext`,
  `AttemptContext`, `SessionPool`, and `RateProfile` in JSON/Markdown reports.
- Pyaterochka visual smoke now includes the same platform context in
  JSON/Markdown reports.
- Shared platform report helpers live in `utils.platform_reporting`, so smoke
  and future parser flows can attach run/session/rate context consistently.
- Shared safe network capture helpers live in `utils.network_capture`, covering
  diagnostic URL masking, empty product payload detection, API discovery
  response capture, request failure capture, and proxy preflight.
- Shared network summary and proxy health classification helpers live in
  `utils.network_diagnostics`, covering response status groups, request failure
  groups, product API samples, empty product payload samples, estimated response
  bytes, and practical proxy traffic-risk classification.
- Persisted proxy history lives in `utils.proxy_history`. It stores a proxy hash
  and masked proxy only, then records success rate, response counts, estimated
  bytes, risk level and last successful attempts in `data/proxy_history.db`.
- Site error tracking lives in `utils.site_error_tracking`. It normalizes
  navigation errors, proxy failures, HTTP 403/407/429/5xx, request failures,
  challenge reasons, empty product payloads and discovery misses into one
  report block. It also accepts normalized Playwright/Chrome DevTools MCP
  console and network observations through `browser_observations`.
- Pyaterochka page context extraction lives in `utils.page_context`.
- Product card lookup and sample extraction live in `utils.product_sampling`.
- The discovery flow still opens visible Camoufox and keeps the same manual
  captcha workflow.
- The main parser runtime is unchanged.

## Next Refactor Order

1. Replace legacy `utils/session_manager.py` with the new `SessionPool` after
   tests cover the behavior that is still needed.
2. Choose one canonical parser base contract and make `main.ParserFactory`
   import checks clean for all stores.
3. Build a dedicated data interception layer from the current passive discovery
   helpers: route/API classifier, response sampler, schema detector, request
   replay candidate collector, and safe product payload archive.
4. After Pyaterochka product API discovery captures real product payloads,
   build API-first extraction and leave DOM extraction as fallback.

## Acceptance Gates

- `pytest` stays green.
- `architecture_check.py` has no `error` findings.
- Warnings are allowed while legacy code is being retired, but each warning
  should map to a known refactor target.
- Reports must continue masking proxies and must not store cookies, captcha
  tokens, auth headers or profile data.
