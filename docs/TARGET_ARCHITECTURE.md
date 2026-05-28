# ParserRIba Target Architecture

Date: 2026-05-26

## Doctrine

ParserRIba is a local Windows desktop program, not a collection of legacy CLI
parsers. The user-facing product starts in the launcher and moves through one
canonical workflow:

`Launcher -> Task Orchestrator -> Browser/Discovery Core -> Store Adapter -> Product Core -> Filter Core -> Report Core -> Storage/Profile Core`

The old CLI/parser stack is not a product runtime. It can remain only as a
temporary reference while useful mechanics are extracted, then it should move to
`archive/`. The migration order is tracked in
`docs/LEGACY_MIGRATION_BACKLOG.md`.

## Product Workflow

1. The user opens the launcher.
2. The user enters a store website URL.
3. The user clicks `Исследование`.
4. ParserRIba opens the site through the local Camoufox runtime.
5. ParserRIba discovers menu, catalog, category and API evidence.
6. ParserRIba creates or updates a local store profile.
7. The launcher shows the full discovered catalog tree.
8. The user selects any needed catalog nodes.
9. ParserRIba collects full product cards from selected nodes.
10. ParserRIba builds dynamic filters from collected product fields.
11. The user selects exact products.
12. ParserRIba exports Excel/JSON/report artifacts and keeps price history.

All visible launcher text must be clear Russian. Internal evidence, strategy
metadata and protection diagnostics belong in stored profile/snapshot data, not
in the simple user surface.

## Target Layers

### Launcher

Owns the desktop UI and the guided workflow. It never calls store scripts
directly. It talks to the task orchestrator and renders normalized task state.

Current path: `launcher/`.

### Task Orchestrator

Owns local task invocation, result normalization, cancellation/timeout policy
and launcher-safe errors.

Current paths: `utils/launcher_task_controller.py`,
`utils/local_task_adapter.py`, `utils/local_task_registry.py`.

### Browser Core

Owns Camoufox launch, persistent profiles, proxy/GeoIP handling, human-like
behavior, manual captcha waits and protection diagnostics.

Current reusable sources: `utils/camoufox_launcher.py`,
`utils/human_behavior.py`, `utils/proxy.py`, `utils/geoip.py`,
`utils/session_pool.py`.

### Discovery Core

Owns store-neutral site research: DOM/menu traversal, embedded JSON extraction,
network evidence capture, route hints, protection signals and catalog graph
building.

Current path: `utils/catalog_tree_discovery/`.

### Catalog Core

Owns catalog tree normalization, selected-node state, route/API hints and
profile-ready catalog snapshots.

Current sources: `models/catalog_discovery.py`,
`utils/catalog_discovery.py`, `utils/store_catalog_registry.py`.

### Store Adapters

Own store-specific extraction behavior behind generic contracts. A store adapter
may use special knowledge from `knowledge_base/`, but it must not become the
global architecture.

Current adapter: Pyaterochka through `utils/pyaterochka_catalog_capture.py` and
`utils/pyaterochka_export.py`.

### Product Core

Owns product card collection and normalized product fields while preserving raw
store-specific fields for future filters and reports.

Current sources: `models/schemas.py`, `utils/pyaterochka_export.py`.

Launcher-facing product cards are mirrored into
`LauncherAppState.products.items`. The desktop `Товары` table and product-card
details read this structured workspace first, with exported JSON kept as a
compatibility artifact and report source.

Dynamic filter counts and discovered raw-field filters are built from the same
collected product workspace whenever product cards are already available.

### Filter Core

Owns dynamic filters derived from collected product data. Filters are not
hardcoded guesses and should honestly handle missing fields.

Current sources: `launcher/desktop_dynamic_filter_panel.py`,
`launcher/desktop_export_facets.py`, `utils/report_filter_facets.py`.

### Report Core

Owns Excel/JSON/report output from selected or filtered products.

Current sources: `utils/storage_report_builder.py`, `utils/excel_report.py`,
`utils/report_export_summary.py`.

Report and filter task wrappers must use explicit launcher selection only. They
must not synthesize default fish/wine categories when the user has not chosen
catalog nodes.

### Storage/Profile Core

Owns SQLite product state, price history, discovery sessions, store profiles,
snapshots and settings. SQLite remains the v1 local database.

Current sources: `utils/product_storage.py`,
`utils/discovery_profile_repository.py`, `utils/onboarding_storage.py`,
`utils/launcher_settings.py`.

## Legacy Policy

The following are not product runtime layers:

- `main.py`
- `parsers/`
- `strategies/`
- `policies/`
- legacy session/export/probe helpers already listed in the flow map

Do not fix legacy bugs for their own sake. If useful behavior exists there,
extract it into a target core or store adapter with tests. Then move the legacy
file to `archive/` in a small, verified slice. Use
`docs/LEGACY_MIGRATION_BACKLOG.md` as the source of truth for move order.

## Near-Term Refactor Rules

- Do not move dense active packages all at once.
- Before each move, check imports with `rg` and regenerate
  `docs/PROJECT_FILE_FLOW_MAP.md`.
- Active runtime must not import from `archive/`.
- Pyaterochka protected behavior must remain available through the store adapter
  while generic cores mature.
- Packaging, dependency hardening and installer work wait until the launcher
  workflow is useful end-to-end.
