# ParserRIba Target Architecture

Date: 2026-06-01

## Doctrine

ParserRIba is a local Windows desktop program, not a collection of legacy CLI
parsers. The user-facing product starts in the launcher and moves through one
canonical workflow:

`Launcher -> Task Orchestrator -> Browser/Discovery Core -> Store Adapter -> Product Core -> Filter Core -> Report Core -> Storage/Profile Core`

The old CLI/parser stack is not a product runtime. Useful mechanics must be
extracted into target cores or store adapters before use. Removed legacy source
is available through git history, not a tracked runtime folder.

Threading and data-flow boundaries are part of the architecture, not an
implementation detail. Launcher V3 must follow
`docs/DATA_FLOW_THREADING_PLAN.md`: workers, subprocesses and browser runtimes
return data, while only the GUI thread renders or mutates Qt widgets.

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
It owns Qt widgets only on the GUI thread.

Current path: `launcher/`.

Current visible flow: `Исследование -> Каталог -> Товары -> Отчёт`.
The `Товары` workspace owns both product selection and filters. The `Отчёт`
workspace owns report-column selection and final export.

### Task Orchestrator

Owns local task invocation, result normalization, cancellation/timeout policy
and launcher-safe errors.
It returns serializable results and must not receive Qt objects.

Current paths: `utils/launcher_task_controller.py`,
`utils/local_task_adapter.py`, `utils/local_task_registry.py`.

### Browser Core

Owns Camoufox launch, persistent profiles, proxy/GeoIP handling, human-like
behavior, manual captcha waits and protection diagnostics.
It must not import desktop launcher modules or mutate launcher state directly.

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
`stores/pyaterochka/product_export.py`.

### Product Core

Owns product card collection and normalized product fields while preserving raw
store-specific fields for future filters and reports.

Current sources: `models/schemas.py`, `stores/pyaterochka/product_export.py`,
`utils/product_raw_fields.py`.

Launcher-facing product cards are mirrored into
`LauncherAppState.products.items`. The desktop `Товары` table and product-card
details read this structured workspace first, with exported JSON kept as a
compatibility artifact and report source.

Dynamic filter counts and discovered raw-field filters are built from the same
collected product workspace whenever product cards are already available.

### Filter Core

Owns dynamic filters derived from collected product data. Filters are not
hardcoded guesses and should honestly handle missing fields.

Current sources: `launcher/desktop_filter_panel.py`,
`launcher/desktop_filter_slots.py`, `launcher/desktop_export_facets.py`,
`launcher/desktop_product_filtering.py`, `utils/site_filter_facets.py`,
`utils/site_filter_descriptors.py`, `utils/report_filter_facets.py`.

Site-provided facets are represented as descriptors and only mapped filters may
locally narrow already collected products. Technical facet metadata must stay
out of the user-facing filter panel.

Launcher filter compatibility aliases, including old `wine_styles` data loaded
from saved manifests, must be centralized in `launcher/desktop_filter_aliases.py`
instead of being reimplemented in multiple launcher modules.

### Report Core

Owns Excel/JSON/report output from selected or filtered products and the
selected report-column contract.

Current sources: `utils/storage_report_builder.py`, `utils/generic_excel_report.py`,
`utils/excel_report.py`, `utils/report_excel_router.py`,
`utils/report_export_summary.py`, `launcher/desktop_report_panel.py`,
`launcher/desktop_report_columns.py`.

Report and filter task wrappers must use explicit launcher selection only. They
must not synthesize default fish/wine categories when the user has not chosen
catalog nodes.

Report columns come from base product fields, useful raw fields and discovered
filter fields. Profiles should later persist user-selected column sets.

### Storage/Profile Core

Owns SQLite product state, price history, discovery sessions, store profiles,
snapshots and settings. SQLite remains the v1 local database.

Current sources: `utils/product_storage.py`,
`utils/discovery_profile_repository.py`, `utils/onboarding_storage.py`,
`utils/launcher_settings.py`, `utils/launcher_profile_snapshot.py`.

StoreProfile should become the owner for catalog snapshots, selected nodes,
product workspace snapshots, dynamic filters, report-column presets,
diagnostics and price-history snapshots.

Workspace favorites extend the Storage/Profile Core as a workspace-scoped user
shortcut layer above store profiles. Favorite stores, catalog nodes and
products must keep their owning workspace/profile context, must not fall back
to a default store, and must refresh only through the target store adapter when
that adapter supports the requested target type.

Launcher themes are a launcher concern, not store profile data. Light and dark
theme preferences should be stored as local launcher settings and applied
through centralized launcher theme tokens rather than scattered widget colors.

## Legacy Policy

The following are not product runtime layers:

- removed `main.py`
- removed `parsers/`
- legacy session/export/probe helpers already listed in the flow map

Do not fix legacy bugs for their own sake. If useful behavior exists there,
extract it into a target core or store adapter with tests. Then remove the
obsolete source in a small, verified cleanup slice. Use
`docs/WORKSPACE_CLEANUP_INVENTORY.md` for current cleanup evidence.

## Near-Term Refactor Rules

- Do not move dense active packages all at once.
- Any new feature that replaces old behavior must define the new contract,
  switch active callers to it, then remove the replaced path in the same slice
  or the next explicit cleanup slice.
- Do not keep two active implementations with unclear priority. If an old path
  must remain temporarily, document the exact blocker and removal condition in
  `docs/NEXT_STEPS.md` or `docs/WORKSPACE_CLEANUP_INVENTORY.md`.
- Before each move, check imports with `rg` and regenerate
  `docs/PROJECT_FILE_FLOW_MAP.md`.
- Active runtime must not import from removed legacy paths.
- Active shared runtime roots must not import store-specific adapter modules
  directly. Store-specific imports belong in adapter-owned paths or the explicit
  lazy registry boundary.
- Runtime task status mapping must not show `empty`, blocked or unsupported
  product collection as successful collection.
- Pyaterochka protected behavior must remain available through the store adapter
  while generic cores mature.
- Packaging, dependency hardening and installer work wait until the launcher
  workflow is useful end-to-end.
