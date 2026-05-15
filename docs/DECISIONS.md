# ParserRIba Decisions

Date: 2026-05-15

## Accepted Decisions

1. Runtime browser stays Python + Camoufox.
   Chrome DevTools MCP and Playwright MCP are diagnostics tools, not the parser
   runtime for protected stores.

2. Pyaterochka is the first hard target.
   Stabilize one difficult store before expanding the architecture across all
   stores.

3. No paid external services without explicit approval.
   This includes cloud scraping browsers, anti-captcha services, hosted LLMs and
   paid APIs.

4. Store secrets outside Git.
   `.env`, proxy credentials, cookies, captcha tokens, browser profiles, logs,
   mmdb files and generated reports are local-only.

5. Diagnostics first, backend later.
   Build reliable local reports, proxy history, site error tracking and
   interception before FastAPI/Postgres/dashboard work.

6. SQLite before Postgres.
   Prove product, price-history and diagnostics schemas locally before migrating
   to Postgres and Alembic.

7. API-first extraction after passive discovery.
   Do not replay protected requests automatically until safe product payload
   candidates are captured and headers/cookies are confirmed unnecessary for the
   replay path.

8. Skills are project helpers.
   Local skills guide Codex work across chats, but they are not runtime features
   shipped to users.

## Open Decisions

- Exact SQLite product and price-history schema.
- Whether Pyaterochka can be extracted through API-first flow or needs DOM
  fallback for some categories.
- Which second store should be stabilized after Pyaterochka.
- When to move from local SQLite to Postgres.
- When to build GUI/installer after parser reliability improves.
