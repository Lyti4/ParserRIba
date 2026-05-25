# ParserRIba Roadmap V1

Date: 2026-05-20

## Purpose

This is the delivery roadmap for the current ParserRIba stage. The primary
target architecture and layer doctrine live in `docs/TARGET_ARCHITECTURE.md`.
Use this file for delivery order and the target architecture for boundaries.

Launcher V2 details are tracked in
`docs/superpowers/specs/2026-05-23-launcher-v2-discovery-workflow-design.md`.
Older launcher and walker plans in `archive/project_history/superpowers/plans/`
are retained as implementation history only.

## Current Product Direction

ParserRIba v1 is a local-first Windows desktop application. The canonical
product flow is:

`Launcher -> Task Orchestrator -> Browser/Discovery Core -> Store Adapter -> Product Core -> Filter Core -> Report Core -> Storage/Profile Core`

The target user experience is: enter a store URL, research the site through the
project browser/runtime, build a local store profile with discovered catalog
and API knowledge, choose discovered categories, collect full product cards for
those categories, derive filters from the collected data, let the user select
specific products, and export an Excel/report table for that selected set.

Current priorities:

1. Keep Pyaterochka stable.
2. Keep scraping runtime local: Python + Camoufox.
3. Ship Launcher V2 over generic site profiles, catalog trees, product
   workspaces, dynamic filters and report contracts.
4. Use local SQLite, JSON, and Excel as the main artifacts.
5. Expand to additional stores only through the onboarding/discovery path.

For Pyaterochka, "stable" means preserving protected-store mechanics as reusable
behavior behind a store adapter: Camoufox configuration, RU proxy and GeoIP
handling, persistent profile/session reuse, human-like behavior, safe
interception, API-first candidate extraction, DOM fallback and anti-bot/proxy
reporting. The old parser layer itself is not the product runtime and should be
archived after useful mechanics are extracted.

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

The current code still lives in transitional folders, but the target product
architecture is split into the cores described in `docs/TARGET_ARCHITECTURE.md`.
Legacy parser files are not a product layer.

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
- Launcher V2 exposes one profile workspace per site/domain and keeps catalog
  tree selection, product workspace, dynamic filters, diagnostics and price
  history isolated per profile.
- Pyaterochka export actions may keep using the existing local task and store
  backend path as a temporary adapter until the generic selected-node product
  collection contract is reliable.

### 2. Local Task Layer

- Local tasks are registered in `utils.local_task_registry`.
- Each task returns a `RunManifest`.
- Current task families:
  - onboarding discovery;
  - Pyaterochka fish export;
  - Pyaterochka wine export;
  - report export from SQLite.

### 3. Store Adapter Layer

- Store-specific runtime logic stays behind store adapters.
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

0. Treat `docs/TARGET_ARCHITECTURE.md` as the source of layer boundaries.
1. Keep task and launcher contracts stable.
2. Finalize one normalized launcher view-model over task results.
3. Rebuild the PySide6 shell as Launcher V2:
   `Исследование -> Каталог -> Товары -> Фильтры -> Отчёт`.
4. Add profile selection/settings before adding more visible runtime controls.
5. Add checkbox catalog tree multi-selection and product workspace state.
6. Add one dynamic scrollable filter panel derived from collected product data.
7. Keep report generation working from SQLite without requiring new live
   scraping.
8. Add one more real store through discovery-first onboarding after the
   Launcher V2 flow is usable for Pyaterochka.
9. Archive legacy parser/strategy/policy files once active imports are removed.
10. Only then move to packaging, installer, and release flow.
