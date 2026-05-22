# ParserRIba Launcher Architecture

Date: 2026-05-22

## Purpose

This document fixes the current launcher architecture in explicit terms:

- what the user does;
- which layer receives that input;
- which task runs;
- what artifacts are produced;
- what data returns to the UI.

Use this file before changing launcher UX, onboarding/discovery flow, export
flow, or report/filter behavior.

## Current Layers

ParserRIba desktop flow is:

`PySide6 Launcher -> Desktop Controller -> Launcher Task Controller -> Local Task Adapter -> Local Task Registry -> Store/Onboarding Runtime -> Storage/Artifacts -> Normalized Launcher View`

### 1. PySide6 Launcher

Files:

- `launcher/desktop_launcher.py`
- `launcher/desktop_window_sections.py`
- `launcher/desktop_filter_panel.py`
- `launcher/desktop_result_table.py`
- `launcher/desktop_view_helpers.py`

Responsibilities:

- render visible controls;
- collect user selection and filters;
- delegate actions to the desktop controller;
- render current task state, result summary, and result rows.

The launcher must not call runtime scripts or store backends directly.

### 2. Desktop Controller

Files:

- `launcher/desktop_controller.py`
- `launcher/desktop_controller_helpers.py`
- `launcher/desktop_export_facets.py`

Responsibilities:

- own launcher state transitions;
- decide which launcher action is available now;
- invoke launcher-facing task actions;
- merge task results into one UI state;
- keep the UI free of subprocess/runtime details.

### 3. Launcher Task Controller

Files:

- `utils/launcher_task_controller.py`
- `utils/local_task_adapter.py`
- `utils/launcher_task_view.py`

Responsibilities:

- convert controller calls into local task invocations;
- normalize task manifests into `LocalTaskProcessResult`;
- expose first-class launcher fields:
  - `category_tree`
  - `selected_categories`
  - `catalog_discovery`
  - `report_summary`
  - `export_summary`
  - `available_filter_counts`
  - `launcher_view`

### 4. Local Task Registry

Files:

- `utils/local_task_registry.py`
- `scripts/run_local_task.py`

Responsibilities:

- register callable local tasks;
- validate task input shape;
- run one task and return `RunManifest`.

Current task families:

- `site_onboarding_discovery`
- `pyaterochka_fish_export`
- `pyaterochka_wine_export`
- `store_report_export`
- `store_report_filter_options`

### 5. Runtime Layer

Files:

- `utils/site_onboarding.py`
- `utils/catalog_discovery.py`
- `utils/store_export_runtime.py`
- `utils/storage_report_builder.py`
- `utils/product_storage.py`

Responsibilities:

- discover catalog structure for one site;
- run store-specific export capture;
- persist products to SQLite;
- build reports and filter options from storage.

### Pyaterochka Runtime Preservation

Pyaterochka is the protected-store runtime baseline. The launcher must keep
using the same local task and store backend path that preserves:

- Camoufox launch options from `utils.camoufox_launcher`;
- RU proxy, GeoIP, persistent profile and session reuse behavior;
- human-like waits, scrolling, hover and cooldown logic;
- safe network/API interception and product API candidate capture;
- DOM/card fallback and error/proxy/anti-bot reporting.

The launcher must not introduce a separate simplified Pyaterochka scraping
path. UI work may change how the user starts research/export/report actions,
but product collection must still go through the existing Pyaterochka runtime
contracts and reports.

### 6. Storage And Artifacts

Files / paths:

- `data/products.db`
- `data/*.json`
- `data/reports/*.xlsx`
- onboarding session state in `data/...`

Responsibilities:

- persist product snapshots;
- persist onboarding sessions;
- produce user-openable artifacts;
- provide report/filter data without mandatory live re-scraping.

## Current User Flow

### Flow A: Catalog research

1. User enters `site_url`.
2. User chooses `shop` and `intent`.
3. Launcher triggers `site_onboarding_discovery`.
4. `utils/site_onboarding.py`:
   - matches known store site if possible;
   - runs discovery or known-site resolution;
   - builds `category_tree`;
   - writes onboarding session state.
5. Manifest summary returns:
   - `category_tree`
   - `category_count`
   - `catalog_discovery`
   - `selected_categories`
6. Launcher shows discovered sections.

### Flow B: Product collection

1. User chooses discovered categories.
2. Launcher triggers live export per selected category.
3. Store runtime writes:
   - JSON export
   - SQLite product state
   - run manifest
4. Controller merges per-category results into one export result.
5. Launcher receives:
   - `export_summary`
   - fresh `available_filter_counts`
   - artifact paths

### Flow C: Narrow selection and report

1. User chooses post-capture filters.
2. Launcher triggers:
   - `store_report_filter_options` to inspect available values;
   - `store_report_export` to build Excel from SQLite.
3. Report layer returns:
   - `report_summary`
   - Excel path
   - categories and counts
4. Launcher opens Excel or folder.

## Target Operator Flow

The intended product flow is a guided workflow for a non-technical user:

1. The user opens the launcher, enters a store website URL, and clicks the
   research action.
2. ParserRIba opens the site through the project browser/runtime path and tries
   to understand the catalog surface:
   - browser-rendered links;
   - navigation/menu/category URLs;
   - intercepted API URLs and response candidates;
   - catalog categories and subcategories;
   - store-specific constraints such as region gate, anti-bot challenge or
     PDF/flipbook catalog.
3. ParserRIba creates or updates a local store profile from the research run.
   The profile stores the discovered catalog tree, useful route/API markers,
   known category URLs, run diagnostics and payload hints. It must not store
   secrets, raw proxy credentials, cookies or captcha tokens.
4. The launcher shows the discovered category/subcategory tree. Nothing is
   pre-selected by default.
5. The user selects the categories and subcategories they need.
6. ParserRIba collects products only from the selected categories through the
   existing store runtime path.
7. Product collection aims to capture full product cards, not only name and
   price. The normalized product data should keep fields when available:
   - producer, manufacturer, supplier, vendor and brand;
   - production country/region/place;
   - category and subcategory;
   - price, unit, discount and stock state;
   - product URL and image URL;
   - fish-specific variants and attributes;
   - wine-specific attributes such as color, style, sugar class, alcohol type
     and other detected variants;
   - raw/store-specific attributes that are useful but not normalized yet.
8. ParserRIba writes the collected products to local storage and builds a
   narrowed product workspace for only the selected categories.
9. The launcher derives filters from the collected data, not from hardcoded
   guesses. Missing fields are shown honestly and do not silently exclude
   products in default mode.
10. The user filters and selects the exact products needed for the final report.
11. ParserRIba exports an Excel/report table for those selected products and
    keeps the store profile available for future runs.

This flow is the target behavior. Current launcher work should move toward it
incrementally without breaking the protected Pyaterochka runtime.

## Current Mismatch With Desired Product

The user wants a strict site-first flow:

1. enter store URL;
2. research store/catalog;
3. choose needed sections;
4. collect products across those sections;
5. narrow the result by supplier/brand/etc.;
6. build final report.

The current code still contains category-first fallbacks:

- launcher can show categories before research;
- backend/category resolvers can inject default categories;
- launcher can auto-select categories in some paths;
- report/filter actions can appear meaningful before fresh product collection.

This is why the launcher can feel "pre-filled" instead of truly researched.

## Required V1 Launcher Contract

The launcher must behave as a staged workflow:

### Stage 1: Исследование магазина

- input:
  - `site_url`
  - `shop`
  - `intent`
- output:
  - `category_tree`
  - `catalog_discovery`
  - store profile update with discovered category URLs, route/API markers and
    payload hints
  - human-readable diagnostics

### Stage 2: Выбор разделов

- input:
  - only discovered categories for the current research session
- output:
  - explicit `selected_categories`

### Stage 3: Сбор товаров

- input:
  - discovered + selected categories
  - runtime settings
- output:
  - export JSON
  - SQLite product state
  - export summary
  - selected-category product workspace
  - filter counts from fresh data

### Stage 4: Узкий отбор и отчёт

- input:
  - post-capture filters
  - explicit selected products
- output:
  - filtered report summary
  - Excel report for selected products

## Non-Negotiable UI Rules

1. Before store research, launcher categories must not be silently injected from
   defaults.
2. Launcher must not auto-select categories for the user.
3. Research action must be named `Исследование`.
4. Export/report actions must operate on explicitly selected discovered
   categories.
5. Filter options must be explained as empty/unavailable until data has really
   been collected.
6. Pyaterochka export actions must preserve the existing protected-store
   runtime path: Camoufox, RU proxy/GeoIP, human behavior, safe interception,
   anti-bot diagnostics and DOM fallback.
7. Store profiles are built from research and collection evidence. They must
   store catalog/API knowledge and diagnostics, not secrets or raw credentials.
8. Filters and final product selection must be based on collected product data
   from the selected categories, not on hardcoded assumptions.

## Near-Term Implementation Order

1. Make launcher category UI discovery-first.
2. Rename onboarding UX to research UX.
3. Separate staged launcher result areas:
   - research result;
   - export result;
   - report result.
4. Keep storage/report tasks stable while the launcher flow is corrected.
