# ParserRIba Data Flow And Threading Plan

Date: 2026-05-28

## Purpose

This document fixes the data-flow and threading boundaries for Launcher V2.
It exists because the launcher must keep working while long browser, product
collection, filtering, report and storage tasks run around it.

The main invariant:

`Workers, subprocesses and browser runtimes return data. Only the GUI thread renders widgets.`

No future feature may bypass this rule for convenience.

## Runtime Boundaries

### GUI Thread

Owns all PySide6 objects and visual rendering.

Current files:

- `launcher/desktop_launcher.py`
- `launcher/desktop_workflow_tabs.py`
- `launcher/desktop_catalog_tree_widget.py`
- `launcher/desktop_dynamic_filter_panel.py`
- `launcher/desktop_product_details.py`
- `launcher/desktop_result_table_widget.py`

Allowed responsibilities:

- read user input from widgets;
- start launcher actions;
- apply finished task results to visible state;
- create, update and delete Qt widgets/items/models;
- call `_refresh_ui()` and tab rendering helpers;
- show localized user messages.

Forbidden responsibilities:

- run Camoufox/browser tasks directly;
- block on long parsing/export/report work;
- pass Qt widgets into controller, task, storage or browser layers.

### Launcher State Boundary

Owns the launcher-facing exchange state.

Current files:

- `models/launcher_state.py`
- `launcher/desktop_controller.py`
- `launcher/desktop_controller_workspace.py`
- `launcher/desktop_state_readers.py`

Allowed responsibilities:

- keep `LauncherAppState` as the structured state object;
- merge completed task results into state;
- keep catalog, product workspace, filters, report artifacts and profile
  snapshot data separated;
- expose state readers for UI code.

Rules:

- `state.catalog.selected_nodes` is the source for selected catalog nodes.
- `state.products.items` is the source for collected product cards.
- `state.dynamic_filters` is derived from collected products and raw fields.
- `state.selection.selected_product_ids` is the source for final product
  selection.
- `state.result` stores task summaries and artifact references.
- For live progress, workers must emit immutable progress events; the GUI
  thread applies them to state.

### Background Thread

Owns launcher action execution that must not block the GUI event loop.

Current file:

- `launcher/desktop_background_task.py`

Allowed responsibilities:

- run one long launcher action in a `QThread`;
- emit success/failure signals;
- return only plain data, exceptions or task result objects.

Forbidden responsibilities:

- create or mutate Qt widgets;
- call `_refresh_ui()` directly;
- create Qt timers, models or documents;
- retain browser/runtime resources after the action finishes.

Critical rule:

Background callbacks must cross back through a GUI-thread `QObject` slot before
they touch launcher state or widgets.

### Local Task Subprocess

Owns isolated task execution for discovery, product collection and reports.

Current files:

- `scripts/run_local_task.py`
- `utils/local_task_registry.py`
- `utils/local_task_adapter.py`
- `utils/launcher_task_controller.py`

Allowed responsibilities:

- validate task input;
- run one task family;
- write JSON/Excel/SQLite artifacts;
- return a `RunManifest` and normalized `LocalTaskProcessResult`.

Forbidden responsibilities:

- import launcher widgets;
- depend on GUI state;
- return non-serializable browser or Qt objects.

### Browser Runtime

Owns Camoufox and Playwright-compatible browser operations.

Current sources:

- `utils/camoufox_launcher.py`
- `utils/catalog_tree_discovery/`
- `utils/pyaterochka_catalog_capture.py`
- `stores/pyaterochka/product_export.py`
- `utils/human_behavior.py`

Allowed responsibilities:

- launch Camoufox;
- handle proxy/GeoIP/profile options;
- perform human-like navigation;
- capture network and DOM evidence;
- detect protection signals;
- collect product data through store adapters.

Forbidden responsibilities:

- import desktop launcher modules;
- update launcher state directly;
- show GUI dialogs;
- solve captcha automatically.

### Storage And Artifacts

Owns persistent local data and user-openable files.

Current files:

- `utils/product_storage.py`
- `utils/discovery_profile_repository.py`
- `utils/launcher_profile_snapshot.py`
- `utils/storage_report_builder.py`
- `utils/excel_report.py`

Allowed responsibilities:

- write SQLite snapshots and price history;
- write JSON and Excel artifacts;
- load previous profile state;
- keep raw product fields so filters and reports do not lose detail.

Forbidden responsibilities:

- import or mutate launcher widgets;
- store secrets, raw proxy credentials, cookies or captcha tokens.

## Canonical Action Flow

Every launcher action follows the same direction:

1. GUI thread reads widgets and updates request state.
2. GUI thread disables conflicting controls.
3. GUI thread starts `start_background_action(...)`.
4. Background thread calls controller/task bridge code.
5. Controller invokes local task or pure state helper.
6. Local task runs browser/storage/report code if needed.
7. Local task returns manifest/result data.
8. Background thread emits success or failure.
9. GUI-thread callback slot applies result to `LauncherAppState`.
10. GUI thread calls `_refresh_ui()` and renders widgets from structured state.

No step may call backward into an earlier layer except by returning data.

## Product Data Flow

### Research

Input:

- `site_url`
- selected store profile
- research mode and runtime settings

Output:

- full catalog tree;
- route/API hints;
- protection and evidence diagnostics;
- profile snapshot update.

State targets:

- `state.catalog.full_tree`
- `state.catalog.full_links`
- `state.profile`
- `state.result`

### Catalog Selection

Input:

- checked catalog nodes from the GUI tree.

Output:

- selected nodes with at least `name` and `url`.

State target:

- `state.catalog.selected_nodes`

### Product Collection

Input:

- `state.catalog.selected_nodes`
- runtime settings;
- store adapter.

Output:

- product cards;
- product count;
- source category list;
- JSON/SQLite artifacts;
- dynamic filter candidates.

State targets:

- `state.products.items`
- `state.products.discovered_fields`
- `state.dynamic_filters`
- `state.result.export_summary`

### Filtering

Input:

- `state.products.items`
- user-selected filter values.

Output:

- current filtered product workspace;
- filter summary for UI.

State targets:

- `state.dynamic_filters.selected_values`
- `state.products.filtered_ids` or an equivalent future workspace field.

Filtering must not delete the original collected products.

### Report

Input priority:

1. `state.selection.selected_product_ids`, when not empty;
2. current filtered product workspace;
3. collected products as a fallback only when the user explicitly asks.

Output:

- Excel path;
- JSON path when requested;
- report summary;
- profile artifact history update.

State targets:

- `state.result.report_summary`
- profile snapshot artifacts.

## Rules For Future Changes

1. New launcher actions must go through `start_background_action(...)` or an
   equivalent GUI-safe action runner.
2. Background workers must not call launcher rendering methods directly.
3. Background callbacks must land in GUI-thread `QObject` slots before state or
   widget mutation.
4. Browser/runtime code must return serializable data, not browser handles.
5. Store adapters must receive explicit selected catalog nodes; no hidden
   fish/wine/default category fallback.
6. Dynamic filters must be derived from collected products and raw fields.
7. Report export must use selected product ids or the current filtered
   workspace.
8. Live progress must be modeled as immutable events, not direct cross-thread
   state mutation.
9. Any new progress/event bridge needs tests proving callback thread affinity.
10. User-facing state names must be localized to clear Russian. Internal values
    such as `discovery_only` may be stored but not shown raw to the user.

## Acceptance Tests To Preserve

The following behaviors must remain covered as the launcher grows:

- background action callbacks run on the GUI thread;
- selected catalog node URLs reach product collection;
- several selected nodes are collected without replacing each other;
- collected products appear in `state.products.items`;
- the `Товары` tab reads structured products before JSON fallback;
- filters are derived from collected products;
- report export receives selected product ids;
- empty catalog selection does not trigger default category export;
- profile snapshots store catalog, products, filters and report artifacts.

## Near-Term Follow-Up

1. Split long launcher controller tests so architecture checks stay clean.
2. Add a typed progress/event model before adding live streaming progress.
3. Audit `_refresh_ui()` for heavy table/filter work that may need batching.
4. Keep local tasks as the boundary for browser/runtime work until there is a
   measured reason to introduce a different worker model.
