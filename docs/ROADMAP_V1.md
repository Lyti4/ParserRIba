# ParserRIba Roadmap V1

Date: 2026-05-20

## Purpose

This is the primary architecture and delivery roadmap for the current ParserRIba
stage. Use this file as the first architecture reference when continuing work,
reviewing scope, or deciding whether a change belongs in v1 or later.

## Current Product Direction

ParserRIba v1 is a local-first Windows desktop application. The working shape
is:

`Desktop Launcher -> Local Task/Actor -> Store Backend -> Storage -> Reports`

The target user experience is: enter a store URL, research the site through the
project browser/runtime, build a local store profile with discovered catalog
and API knowledge, choose discovered categories, collect full product cards for
those categories, derive filters from the collected data, let the user select
specific products, and export an Excel/report table for that selected set.

Current priorities:

1. Keep Pyaterochka stable.
2. Keep scraping runtime local: Python + Camoufox.
3. Ship a simple Windows launcher over the existing task/runtime contracts.
4. Use local SQLite, JSON, and Excel as the main artifacts.
5. Expand to additional stores only through the onboarding/discovery path.

For Pyaterochka, "stable" explicitly means preserving the protected-store
mechanics already built into the parser path: Camoufox configuration, RU proxy
and GeoIP handling, persistent profile/session reuse, human-like behavior,
safe interception, API-first candidate extraction, DOM fallback, and
anti-bot/proxy/error reporting. The launcher is a control surface over that
runtime; it must not replace it with a separate simplified scraping path.

What is explicitly out of scope for v1:

- paid scraping/captcha/browser APIs;
- cloud LLM services;
- mandatory remote backend;
- multi-user web dashboard;
- server-side worker fleet.

External developer tools are governed separately by `docs/TOOLS_POLICY.md`.
They may assist coding and review work, but they are not runtime dependencies
unless promoted by an explicit decision.

## Runtime Architecture

The current architecture is split into five layers.

### 1. Launcher Layer

- User first researches one store URL and catalog intent.
- Launcher then shows discovered sections from that research result.
- User chooses sections only after discovery.
- User chooses report filters only after products have been collected.
- User chooses final report products only after products have been collected
  and narrowed through real data filters.
- Launcher is a Windows desktop UI, not a web app.
- Preferred GUI stack for v1: `PySide6`.
- Launcher does not call store scripts directly.
- Launcher calls `utils.launcher_task_controller`.
- Launcher reads one normalized task result shape from `launcher_view`.
- Launcher export actions for Pyaterochka keep using the existing local task
  and store backend path, including Camoufox, proxy/GeoIP, human behavior,
  interception and anti-bot diagnostics.

### 2. Local Task Layer

- Local tasks are registered in `utils.local_task_registry`.
- Each task returns a `RunManifest`.
- Current task families:
  - onboarding discovery;
  - Pyaterochka fish export;
  - Pyaterochka wine export;
  - report export from SQLite.

### 3. Store Backend Layer

- Store-specific runtime logic stays behind store backends.
- URLs, route markers, category names, and store rules stay in `knowledge_base/`.
- A new store becomes runtime-ready only after discovery confirms real catalog
  structure and useful payload fields.

### 4. Storage Layer

- Current storage is local SQLite in `data/products.db`.
- SQLite remains the v1 database.
- SQLite is the source for:
  - current product state;
  - price history;
  - onboarding session state;
  - store profiles with discovered catalog trees, route/API markers and payload
    hints;
  - launcher-driven report generation.

### 5. Report Layer

- Reports are built from stored product state whenever possible.
- JSON/Excel are local user artifacts.
- Excel generation stack is `openpyxl`.
- Filtering belongs here unless the site reliably supports the same filter as a
  capture boundary.

## Desktop Technology Choices

The expected v1 desktop stack is:

- GUI: `PySide6`
- Browser/runtime scraping: existing `Camoufox` + local task layer
- HTTP/API support: `httpx` where payloads are already understood
- HTML parsing fallback: `BeautifulSoup` where needed
- Database: `SQLite`
- Report generation: `openpyxl`
- Background execution inside launcher: simple worker thread / local task calls
- Packaging: `PyInstaller`
- Installer: `Inno Setup`
- Updates later: `GitHub Releases`

The project does **not** need a special launcher plugin to build this. Current
available plugins are auxiliary only:

- `GitHub` later for release automation;
- `Figma` only if UI mockups are wanted;
- `Browser` is not central because the launcher is desktop, not local web UI.

## Filters And Report Strategy

ParserRIba uses two filter classes.

### Pre-capture filters

These change what the browser tries to collect:

- store;
- catalog intent;
- selected categories;
- attempt count;
- browser mode.

### Post-capture filters

These are applied after data is stored:

- supplier / producer / manufacturer / vendor / brand;
- category;
- price range;
- in-stock state;
- wine style;
- alcohol type;
- sugar class;
- color.

Rule:

- default mode is non-strict;
- missing fields do not exclude a product unless the user explicitly asks for
  strict filtering.

## Installation Strategy

### V1 Local Install

ParserRIba should be installable on another Windows machine as a local app.

Delivery order:

1. development repo + `.venv`;
2. portable ZIP;
3. Windows installer.

Expected local layout:

- launcher entrypoint;
- bundled PySide6 launcher;
- Camoufox runtime/setup check;
- local `data/`, `profiles/`, `logs/`;
- local config and optional proxy setup;
- no secrets in Git.

The first packaged user experience should behave like a normal Windows program:

1. install one `.exe`;
2. open one launcher window;
3. research the store from its URL;
4. create or update the store profile from discovered catalog/API evidence;
5. choose discovered sections;
6. run product collection for those sections;
7. inspect filters derived from collected products;
8. select the exact products for the report;
9. export Excel;
10. open the report folder;
11. keep local settings;
12. show understandable error messages.

### V2 Remote Mode

Server mode is intentionally deferred.

It becomes valid only after:

1. Pyaterochka is stable;
2. at least one more retailer is stable;
3. local task contracts are proven sufficient.

When remote mode starts, it must reuse the same task layer instead of inventing
a separate scraping execution model.

## Store Expansion Rules

For every new retailer:

1. run site onboarding and catalog discovery;
2. classify the surface:
   - normal category tree;
   - API-backed listing;
   - region gate;
   - challenge/block;
   - PDF/flipbook;
3. add runtime backend only after real payloads or stable DOM paths are
   confirmed;
4. keep discovery-only stores out of runtime-ready status.

Example:

- Pyaterochka is runtime-ready.
- Verny remains discovery-only because it currently behaves like a PDF/flipbook
  catalog.

## Near-Term Implementation Order

1. Keep task and launcher contracts stable.
2. Finalize one normalized launcher view-model over task results.
3. Build the first PySide6 launcher shell over the existing local task layer.
4. Keep report generation working from SQLite without requiring new live
   scraping.
5. Add result table, filter state, settings state, and error presentation.
6. Add one more real store through discovery-first onboarding.
7. Only then move to packaging, installer, and release flow.
