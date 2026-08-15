# ParserRIba Legacy Migration Backlog

Date: 2026-05-26

## Purpose

This backlog defines the order for moving obsolete code out of the active
runtime while the launcher-first architecture takes over. The goal is not to
repair the legacy parser stack. The goal is to extract useful mechanics into
target cores and store adapters, then archive the old files in small verified
slices.

Active runtime must not import from `archive/`.

## Keep Active

These paths are part of the current launcher-first product path and should stay
active while the new architecture stabilizes:

- Launcher layer: `launcher/desktop_launcher.py`,
  `launcher/desktop_controller.py`, `launcher/desktop_*panel.py`,
  `launcher/desktop_*helpers.py`.
- Task bridge: `utils/launcher_task_controller.py`,
  `utils/local_task_adapter.py`, `utils/local_task_registry.py`.
- Discovery/catalog core: `utils/catalog_tree_discovery/`,
  `utils/browser_catalog_discovery.py`, `utils/catalog_discovery.py`,
  `models/catalog_discovery.py`, `utils/store_catalog_registry.py`.
- Pyaterochka active adapter: `utils/pyaterochka_catalog_capture.py`,
  `stores/pyaterochka/product_export.py`.
- Product/report/storage core: `models/schemas.py`,
  `utils/product_storage.py`, `utils/discovery_profile_repository.py`,
  `utils/onboarding_storage.py`, `utils/storage_report_builder.py`,
  `utils/excel_report.py`, `utils/report_export_summary.py`,
  `utils/report_filter_facets.py`.
- KB/runtime support: `utils/kb_loader.py`, `utils/kb_interception.py`,
  `utils/camoufox_launcher.py`, `utils/human_behavior.py`,
  `utils/proxy.py`, `utils/geoip.py`.

## Migration Order

### Phase 1: Isolated Legacy Utilities

Candidate files:

- `policies/engine.py`
- `strategies/base_strategy.py`
- `strategies/captcha_handler.py`
- `strategies/pagination_strategy.py`
- `utils/site_probe.py`
- `utils/session_manager.py`

Move only after `rg` confirms no active launcher/discovery/product path imports
them. If a useful idea remains, extract it into Browser Core or Discovery Core
first with tests.

### Phase 2: Old Store Parser Modules

Candidate files:

- `parsers/auchan.py`
- `parsers/lenta.py`
- `parsers/okey.py`
- `parsers/perekrestok.py`

Do not develop these modules further. If route markers, selectors or browser
mechanics are useful, move that knowledge into `knowledge_base/` or a future
store adapter before archiving.

### Phase 3: Parser Bridge

Candidate files:

- `parsers/base.py`
- `parsers/base_parser.py`
- `parsers/camoufox_parser.py`
- `parsers/playwright_parser.py`

These move later because they may still be referenced by the old CLI entrypoint
and tests. Before archiving, remove direct dependencies from active code and
make sure the launcher task path uses target cores/adapters only.

### Phase 4: Pyaterochka Legacy Reference

Candidate file:

- `parsers/pyaterochka.py`

This is reference material only. Do not pull it wholesale into the generic
engine. Extract confirmed useful mechanics into
`utils/pyaterochka_catalog_capture.py`, `stores/pyaterochka/product_export.py`,
Browser Core, or Discovery Core, then archive the legacy file.

### Phase 5: Old Entrypoint

Candidate file:

- `main.py`

Archive only after the launcher-first workflow is the complete documented
runtime and no active tests or diagnostics depend on the old parser stack.

## Per-Slice Checklist

Before moving any file:

1. Run `rg` for imports and direct file references.
2. Confirm the active runtime will not import from `archive/`.
3. Move the smallest safe group, not a whole package at once.
4. Regenerate `docs/PROJECT_FILE_FLOW_MAP.md`.
5. Run targeted tests for touched code.
6. Run the standard validation commands from `docs/NEXT_STEPS.md`.

Do not fix legacy bugs unless the code is being extracted into a target core or
store adapter.
