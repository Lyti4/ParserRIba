# Discovery Intelligence Research Notes

Date: 2026-05-23

These notes describe tools reviewed for the `Исследование` intelligence layer.
They are development references, not runtime dependencies.

## Crawlee

- Useful ideas: request queue/frontier, URL priorities, retry accounting,
  session/proxy state, blocked-request classification, lifecycle hooks and run
  statistics.
- Do not add Crawlee to the ParserRIba runtime in this slice.
- Python Crawlee can run Playwright/Camoufox, but ParserRIba already has a
  Camoufox path with project-specific anti-bot and launcher contracts.

## Browser Events

- First production path remains Playwright-compatible Camoufox hooks:
  `page.on("request")`, `page.on("response")`, `response.text()`, rendered HTML
  capture and script parsing.
- Decode only payload bodies already exposed by browser/network APIs.
- Do not replay protected requests automatically until payload fields and
  header/cookie safety are proven.

## CDP And Extensions

- Chrome Fetch/CDP is a lab tool for diagnostics, not the main runtime, because
  the project browser is Camoufox/Firefox.
- Firefox WebExtension `webRequest` can be explored as an optional manual
  capture adapter if browser events do not expose enough signal.
- Extensions should not become mandatory for launcher users before the core
  Camoufox path is proven insufficient.

## mitmproxy

- mitmproxy can help inspect difficult sites, especially missing response bodies
  or WebSocket payloads.
- Do not embed mitmproxy in the launcher.
- Treat it as an optional diagnostic lab with explicit operator setup.

## Current Implementation Slice

- Keep the runtime free: no paid scraping, captcha, cloud browser or LLM APIs.
- Classify payloads into catalog tree, listing, product, pagination,
  protection and noise.
- Store provenance on internal discovery nodes through evidence refs, source,
  confidence, route hints and protection signals.
- Keep frontier diagnostics in profile notes: enqueued count, pending count and
  skipped reasons such as offsite, repeat limit, already visited and
  product/listing branch.
- Keep user-facing launcher Russian simple; hide low-level evidence unless a
  developer diagnostic view asks for it.
