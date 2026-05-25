# ParserRIba Project Structure

Date: 2026-05-25

This is the active physical map of the project. Use it together with
`docs/PROJECT_FILE_FLOW_MAP.md` before moving or archiving code.

## Active Layers

### Launcher UI

- `launcher/` renders the PySide6 desktop launcher.
- Entry point: `scripts/run_desktop_launcher.py`.
- The launcher must call controller/task APIs, not parser scripts directly.
- Key modules: `desktop_launcher.py`, `desktop_controller.py`,
  `desktop_workflow_tabs.py`, `desktop_catalog_tree_widget.py`,
  `desktop_dynamic_filter_panel.py`, `desktop_product_details.py`.

### Launcher Task Bridge

- `utils/launcher_task_controller.py` converts launcher actions to local tasks.
- `utils/local_task_adapter.py` normalizes task results for the UI.
- `utils/local_task_registry.py` owns callable local task registration.
- CLI entry point: `scripts/run_local_task.py`.

### Catalog Discovery Core

- `utils/catalog_tree_discovery/` is the current store-neutral research core.
- Entry points: `scripts/run_site_onboarding.py`, `utils/site_onboarding.py`,
  `utils/browser_catalog_discovery.py`.
- Responsibilities: DOM/menu discovery, embedded JSON extraction, network
  evidence capture, category graph building and phase events for the launcher.

### Store Adapters

- `utils/pyaterochka_catalog_capture.py` and `utils/pyaterochka_export.py` are
  the current Pyaterochka adapter/reference path.
- `utils/store_catalog_registry.py` and `utils/store_export_runtime.py` expose
  store-specific runtime through generic launcher/local-task contracts.
- Pyaterochka protected-store mechanics must be preserved as reference behavior,
  but they must not become the generic discovery architecture.

### Browser, Session And Protection Support

- `utils/camoufox_launcher.py` centralizes Camoufox launch options.
- `utils/human_behavior.py`, `utils/proxy.py`, `utils/geoip.py`,
  `utils/session_pool.py`, `utils/network_capture.py` and
  `utils/interception.py` support browser and network diagnostics.

### Storage And Reports

- `utils/product_storage.py` owns SQLite product state.
- `utils/storage_report_builder.py`, `utils/report_filter_facets.py`,
  `utils/report_export_summary.py` and `utils/excel_report.py` build reports
  and filter options from stored products.
- Runtime artifacts belong in `data/`, not in Git.

### Domain Models

- `models/` contains Pydantic and task/result contracts.
- Keep public models stable because launcher, tasks, discovery and reports share
  them.

### Knowledge Base

- `knowledge_base/` stores store-specific URLs, selectors, route markers and
  notes.
- `knowledge_base/template.md` is a scaffold template and is intentionally not
  loaded as a store profile.

### Scripts

- `scripts/` contains manual, diagnostic and packaging entry points.
- Scripts may call runtime layers; runtime layers should not depend on scripts
  unless the file is explicitly a diagnostics adapter.

### Tests

- `tests/` mirrors active layers.
- Large tests should be split only after a passing baseline is preserved.

## Legacy Keep-In-Place

These files are legacy or compatibility candidates, but should stay in place
until replacement contracts and tests are ready:

- `main.py`
- `parsers/base.py`
- `parsers/base_parser.py`
- `parsers/camoufox_parser.py`
- `parsers/playwright_parser.py`
- old non-Pyaterochka parsers under `parsers/`
- `policies/engine.py`
- `strategies/`
- `utils/session_manager.py`
- `utils/export.py`
- `utils/site_probe.py`

Reason: some are still imported by compatibility paths or tests, and moving
them now would create noisy import churn without improving the launcher flow.

## Archive

- `archive/project_history/root_docs/` contains superseded root documents.
- `archive/project_history/superpowers/plans/` contains completed plans.
- `archive/project_history/research_notes/` contains old research/report notes.

Do not import from `archive/`. It is retained for human reference only.

## Local Generated Paths

These paths are local artifacts and should not be committed:

- `.playwright-mcp/`
- `ParserRIba Launcher.lnk`
- `data/`
- `generated_scaffolds/`
- `logs/`
- `profiles/`
- `build/`
- `dist/`
