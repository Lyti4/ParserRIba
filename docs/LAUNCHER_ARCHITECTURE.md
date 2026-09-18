# ParserRIba Launcher Architecture

Date: 2026-05-31

## Purpose

This document describes the current Launcher V3 architecture: what the user
does, which layer receives the action, which task runs, what artifacts are
created, and what data returns to the UI.

Use it together with:

- `docs/TARGET_ARCHITECTURE.md`
- `docs/DATA_FLOW_THREADING_PLAN.md`
- `docs/PROJECT_STATE.md`

## Canonical Flow

Visible launcher workflow:

`Исследование -> Каталог -> Товары -> Отчёт`

Layer flow:

`PySide6 Launcher -> Desktop Controller -> Launcher Task Controller -> Local Task Adapter -> Local Task Registry -> Store/Onboarding Runtime -> Storage/Artifacts -> Launcher State`

Only GUI-thread code may mutate Qt widgets. Workers, subprocesses and browser
runtime code return plain data.

## Launcher Layer

Main files:

- `launcher/desktop_launcher.py`
- `launcher/desktop_workspace_shell.py`
- `launcher/desktop_navigation.py`
- `launcher/desktop_command_strip.py`
- `launcher/desktop_inspector_panel.py`
- `launcher/desktop_workflow_tabs.py`
- `launcher/desktop_controller.py`
- `launcher/desktop_controller_*.py`
- `launcher/desktop_catalog_tree_widget.py`
- `launcher/desktop_filter_panel.py`
- `launcher/desktop_filter_slots.py`
- `launcher/desktop_product_filtering.py`
- `launcher/desktop_product_mini_catalog.py`
- `launcher/desktop_product_details.py`
- `launcher/desktop_result_table.py`
- `launcher/desktop_report_panel.py`
- `launcher/desktop_report_columns.py`
- `launcher/desktop_error_panel.py`
- `launcher/desktop_theme.py`

Responsibilities:

- render visible controls in Russian;
- keep the user inside the staged workflow;
- collect catalog, product, filter and report-column selection;
- delegate actions to the controller;
- render normalized launcher state;
- never call store scripts directly.

Current V4 shell contract:

- persistent left navigation rail with active, idle, completed, warning,
  disabled and planned route states;
- compact command strip with user-facing Russian current-state summary:
  outcome, progress, product counts, latest file and next action. Raw profile
  IDs, internal task names and internal phases belong in diagnostics and
  support artifacts, not in the normal top strip;
- main workspace backed by the existing workflow tab stack while migration
  continues;
- route-specific right inspector. Research/catalog/report routes can show
  store/save context where it helps; the products route owns selected-product
  details in the route context so the product table stays primary; diagnostics
  owns error detail;
- diagnostics workspace with masked copyable support text and a separate
  "copy latest error" action;
- centralized modern light/dark QSS tokens for tables, forms, focus, disabled
  controls, route state styling, warnings and scrollbars.

## Controller And Task Bridge

Main files:

- `launcher/desktop_controller.py`
- `utils/launcher_task_controller.py`
- `utils/launcher_report_task_controller.py`
- `utils/local_task_adapter.py`
- `utils/local_task_registry.py`
- `scripts/run_local_task.py`

Responsibilities:

- convert launcher actions into local tasks;
- isolate long work from the GUI thread;
- normalize task manifests into launcher-safe state;
- return errors and warnings as user-readable Russian status plus technical
  diagnostics in state/profile artifacts.

## Runtime Tasks

Current task families:

- `site_onboarding_discovery`
- product collection through the selected store adapter
- `store_report_export`
- report/filter support tasks

Unknown sites stay `discovery_only` until a real product adapter exists.
Generated fake runtime scaffolds are not progress.

## Stage Details

### 1. Исследование

Input:

- site URL;
- store/profile hint when available;
- runtime settings such as headless/manual wait/timeout.

Output:

- discovered catalog/menu/tree;
- route/API hints;
- protection and partial-warning diagnostics;
- profile/discovery snapshot.

### 2. Каталог

Input:

- discovered catalog tree from the current research session.

Output:

- explicit selected catalog nodes with at least `name` and `url`.

Rules:

- nothing should be silently preselected after research;
- product collection must use selected node URLs, not old fixed fish/wine
  categories.

### 3. Товары

Input:

- selected catalog nodes;
- collected products;
- local filter choices.

Output:

- product workspace in `state.products.items`;
- selected product IDs in `state.selection.selected_product_ids`;
- filtered table view;
- selected-filter summary;
- product details with normalized and raw fields.

Rules:

- filters are embedded in this workspace;
- filters apply locally to collected products;
- original collected products are not deleted when filters change;
- site facets that cannot map to product fields must not silently erase the
  table.

### 4. Отчёт

Input:

- selected product IDs, if any;
- otherwise the current filtered product workspace;
- selected report columns.

Output:

- Excel/JSON artifacts;
- report summary;
- file/folder paths for opening generated artifacts.

Rules:

- JSON is an internal artifact, not the primary user experience;
- the user chooses report columns from available product/raw/filter fields;
- report defaults must not fall back to obsolete wine/fish assumptions.

## Pyaterochka Mechanics

Pyaterochka remains the first protected-store runtime adapter. Preserve useful
mechanics through target layers:

- Camoufox launch options;
- persistent profile;
- RU proxy and GeoIP;
- manual captcha wait;
- human-like scrolling/hover/waits;
- safe network/API interception;
- anti-bot/proxy diagnostics;
- DOM fallback when API payloads are incomplete.

Do not rebuild the generic discovery/product core around the old Pyaterochka
parser. Extract only proven mechanics into Browser Core, Discovery Core,
Product Core or `stores/pyaterochka/`.

## Store Profile Direction

Launcher V3 should evolve into a multi-site profile manager. One site/domain
maps to one local StoreProfile.

Profile should own:

- site URL and display name;
- catalog tree and selected nodes;
- route/API hints;
- browser/session/protection diagnostics without secrets;
- latest product workspace;
- found filters and selected filters;
- report-column presets;
- generated artifacts;
- future price-history snapshots.

## Non-Negotiable UI Rules

- All visible user strings are clear Russian.
- No old fixed fish/wine defaults in generic UI.
- No hidden auto-selection after research.
- No blocking browser/storage/report work on the GUI thread.
- No separate old filters tab; filters belong to `Товары`.
- No direct runtime imports from removed legacy paths.
