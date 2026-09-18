# ParserRIba Project Structure

Date: 2026-06-06

This is the active physical map of the project. The target layer doctrine is in
`docs/TARGET_ARCHITECTURE.md`. Use both documents together with
`docs/DATA_FLOW_THREADING_PLAN.md`, `docs/PROJECT_FILE_FLOW_MAP.md` and
`docs/WORKSPACE_CLEANUP_INVENTORY.md` before moving or removing code.

## Active Layers

### Launcher UI

- `launcher/` renders the PySide6 desktop launcher.
- Entry point: `scripts/run_desktop_launcher.py`.
- The launcher must call controller/task APIs, not parser scripts directly.
- Qt widgets belong to the GUI thread only; background actions return data
  through the boundary defined in `docs/DATA_FLOW_THREADING_PLAN.md`.
- Key modules: `desktop_launcher.py`, `desktop_controller.py`,
  `desktop_controller_profile.py`, `desktop_controller_workspace.py`,
  `desktop_workflow_tabs.py`, `desktop_catalog_tree_widget.py`,
  `desktop_filter_panel.py`, `desktop_filter_slots.py`,
  `desktop_product_filtering.py`, `desktop_product_mini_catalog.py`,
  `desktop_product_details.py`, `desktop_result_table.py`,
  `desktop_report_panel.py`, `desktop_report_columns.py`,
  `desktop_favorites.py`, `desktop_theme.py`, `desktop_filter_aliases.py`.
- Visible workflow: `Исследование`, `Каталог`, `Товары`, `Отчёт`.
- Filters are embedded into the `Товары` workspace. Report-column selection is
  embedded into the `Отчёт` workspace.

### Launcher Task Bridge

- `utils/launcher_task_controller.py` converts launcher actions to local tasks.
- `utils/local_task_adapter.py` normalizes task results for the UI.
- `utils/local_task_registry.py` owns callable local task registration.
- The active local task list is store-neutral by default. Pyaterochka-named
  export task names remain runnable compatibility aliases only.
- CLI entry point: `scripts/run_local_task.py`.

### Catalog Discovery Core

- `utils/catalog_tree_discovery/` is the current store-neutral research core.
- Entry points: `scripts/run_site_onboarding.py`, `utils/site_onboarding.py`,
  `utils/browser_catalog_discovery.py`.
- Responsibilities: DOM/menu discovery, embedded JSON extraction, network
  evidence capture, category graph building and phase events for the launcher.

### Store Adapters

- `utils/pyaterochka_catalog_capture.py` and
  `stores/pyaterochka/product_export.py` are the current Pyaterochka
  adapter/reference path.
- `utils/store_catalog_registry.py` and `utils/store_export_runtime.py` expose
  store-specific runtime through generic launcher/local-task contracts.
- Pyaterochka protected-store mechanics must be preserved as reference behavior,
  but they must not become the generic discovery architecture.

### Browser, Session And Protection Support

- `utils/camoufox_launcher.py` centralizes Camoufox launch options.
- `utils/human_behavior.py`, `utils/proxy.py`, `utils/geoip.py`,
  `utils/session_pool.py`, `utils/network_capture.py` and
  `utils/interception.py` support browser and network diagnostics.
- `utils/protected_store_manual_gate.py` owns shared protected-store manual
  challenge readiness for catalog discovery and product collection. Store
  adapters may provide store-specific profiles, but they should not add a
  second polling loop for manual captcha resolution.

### Product, Filters, Storage And Reports

- `utils/product_storage.py` owns SQLite product state.
- `utils/product_raw_fields.py` extracts useful product-card raw fields from
  listing/API payloads; `utils/product_raw_field_config.py` owns its field
  aliases, attribute names and name-derived keyword groups.
- `utils/product_classification.py` is the store-neutral facade used by generic
  launcher/report display code for derived product classifications.
- `utils/site_filter_descriptors.py` and `utils/site_filter_facets.py`
  normalize site-provided filter/facet payloads.
- `launcher/desktop_export_facets.py`, `launcher/desktop_filter_panel.py`,
  `launcher/desktop_filter_slots.py` and `launcher/desktop_product_filtering.py`
  build and apply Launcher V3 product filters.
- Launcher/report filter contracts now expose neutral `subcategories` while
  keeping legacy `wine_styles` synchronized for saved profile/report
  compatibility. `launcher/desktop_filter_aliases.py` owns that compatibility
  alias so old keys do not spread across launcher modules.
- `utils/storage_report_builder.py`, `utils/report_filter_facets.py`,
  `utils/report_export_summary.py`, `utils/generic_excel_report.py`,
  `utils/report_excel_router.py` and `utils/excel_report.py` build reports,
  route generic/wine Excel output and expose filter/report summary data.
- Export/report summaries expose neutral `product_breakdown`; legacy
  `wine_breakdown` remains as a compatibility alias for saved manifests.
  `utils/product_breakdown_summary.py` normalizes old summaries for launcher
  readers.
- `utils/launcher_profile_snapshot.py` writes local Launcher V3 workspace
  snapshots, including workspace pointers plus filter/report-column presets.
- `utils/store_profile_repository.py`, `utils/store_profile_schema.py`,
  `utils/store_profile_writes.py`, `utils/store_profile_payloads.py`,
  `utils/store_profile_sessions.py`, `utils/workspace_journal.py` and
  `utils/store_profile_prices.py` are the central SQLite StoreProfile layer for
  project workspaces, profile versions, catalog snapshots, product workspaces,
  explicit filter/report preset reads and writes, secret-safe workspace journal
  events, price observations and latest-session price comparison.
  `utils/store_profile_workspaces.py` keeps workspace row helpers focused.
- `launcher/desktop_controller_profile.py` saves completed launcher task state
  and explicit manual profile saves into the profile repository, while
  `launcher/desktop_controller_profile_load.py` restores the latest or selected
  saved session without starting browser tasks.
  `launcher/desktop_profile_session_panel.py` renders saved sessions and the
  compact latest-session price-history summary plus workspace profile selector
  for the active workspace/profile.
  `launcher/desktop_workspace_panel.py` renders the compact active workspace
  summary plus recent journal events, `launcher/desktop_workspace_journal.py`
  records launcher journal events, and `launcher/desktop_controller_workspace.py` owns workspace
  controller helpers plus task-result workspace synchronization.
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
- `scripts/codex_rlm_sidecar.py` is Codex-only developer tooling. It may use
  the isolated `tools/rlm-runtime/.venv` environment, but product runtime roots
  must not import `rlm` or `rlms`.

### Tests

- `tests/` mirrors active layers.
- Large tests should be split only after a passing baseline is preserved.

## Removed Legacy

Legacy CLI/parser code and historical project notes are not product runtime
layers and should not remain as tracked working-tree folders. Useful mechanics
must be extracted into target cores or store adapters with tests before removal.
Git history is the long-term archive.

The active cleanup inventory is `docs/WORKSPACE_CLEANUP_INVENTORY.md`. The
active architecture hardening snapshot is
`docs/ARCHITECTURE_HARDENING_AUDIT.md`.

Do not import from removed legacy paths. `scripts/architecture_check.py` blocks
active runtime imports from `archive.*`.

## Local Generated Paths

Source folders are `launcher/`, `models/`, `stores/`, `utils/`, `scripts/`,
`tests/`, `docs/`, `specs/` and `knowledge_base/`. Local runtime, build,
diagnostic and tool-cache folders are not source. Keep them ignored and do not
delete user data blindly during source cleanup.

These paths are local artifacts and should not be committed:

- `.venv/`
- `.build-venv/`
- `.playwright-mcp/`
- `.serena/cache/`
- `.serena/logs/`
- `.serena/memories/`
- `ParserRIba Launcher.lnk`
- `data/`
- `generated_scaffolds/` (legacy local output only; active onboarding does not
  generate backend/capture stub code; removed locally when present)
- `graphify-out/`
- `tools/rlm-runtime/.venv/`
- `logs/`
- `profiles/`
- `build/`
- `dist/`
