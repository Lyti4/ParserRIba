# ParserRIba Next Steps

Date: 2026-05-23

## Active Track

The active track is now launcher-first and core/layer based:

1. keep the launcher as the canonical user entrypoint;
2. extract reusable Pyaterochka mechanics into generic cores and store adapters;
3. rebuild the desktop workflow around strict discovery-first behavior:
   - research store;
   - choose discovered catalog nodes;
   - collect products from selected nodes;
   - narrow the product workspace through dynamic filters;
   - build the final Excel/report output.

Architecture and delivery decisions for this stage are tracked in
`docs/TARGET_ARCHITECTURE.md` and `docs/ROADMAP_V1.md`. Use the target
architecture for layer boundaries and the roadmap for delivery order.

## Immediate Plan

Current Launcher V2 source of truth:

- `docs/TARGET_ARCHITECTURE.md`
- `docs/LAUNCHER_ARCHITECTURE.md`
- `docs/superpowers/specs/2026-05-23-launcher-v2-discovery-workflow-design.md`

Older implementation plans were moved to
`archive/project_history/superpowers/plans/` as history only. They are not the
current source of truth for Launcher V2.

1. Keep the current local task layer stable:
   - onboarding discovery;
   - Pyaterochka fish export;
   - Pyaterochka wine export;
   - report export from SQLite;
   - report filter options.
2. Keep the unified launcher-facing result contract stable:
   - `LocalTaskProcessResult`;
   - first-class `report_summary`, `export_summary`,
     `available_filter_counts`, `category_tree`, `catalog_discovery`;
   - unified `launcher_view`.
3. Rebuild the launcher as Launcher V2:
   - guided tabs: `Исследование`, `Каталог`, `Товары`, `Фильтры`, `Отчёт`;
   - visible store profile context for many future sites;
   - full catalog tree with checkbox multi-selection;
   - no auto-selected categories after research;
   - product collection from checked catalog nodes;
   - one dynamic scrollable filter panel derived from collected product/card
     fields;
   - report generation from selected or filtered products.
4. Make `StoreProfile` the central launcher object:
   - one site/domain maps to one profile;
   - catalog, selected nodes, product workspace, filters, diagnostics and price
     history are isolated per profile;
   - profile settings may include advanced network/proxy diagnostics without
     exposing secrets in the UI or stored artifacts.
5. Keep Pyaterochka mechanics as reference material and expose them through a
   store-specific adapter only:
   - do not make it the generic Launcher V2 engine;
   - extract reusable mechanics only behind generic browser/session/protection
     contracts;
   - archive old parser/runtime files after their useful mechanics are extracted.
6. Continue improving `Исследование` as a store-neutral Camoufox walker:
   - serial single-page browser session;
   - menu expansion before tree capture;
   - bounded category traversal with repeat limits;
   - deep selected-node research for subcategories, breadcrumbs, listing API and
     site facets;
   - launcher-safe phase reporting and partial warnings.
7. Continue using SQLite as the main desktop storage.
8. Defer installer/update work until the launcher MVP is usable end-to-end.

## Next Refactors

- Use `docs/PROJECT_STRUCTURE.md` and `docs/PROJECT_FILE_FLOW_MAP.md` before
  deleting or quarantining code:
  it shows launch paths, local imports, test-only imports and cleanup review
  candidates.
- Use `docs/LEGACY_MIGRATION_BACKLOG.md` for the exact order of legacy archive
  slices.
- Add Launcher V2 state models:
  - profile state;
  - catalog tree selection state;
  - product workspace state;
  - dynamic filter state;
  - task/result state.
- Split the remaining oversized desktop controller surface:
  - move report/filter orchestration out of `launcher/desktop_controller.py`;
  - split `tests/test_desktop_launcher_controller.py` by controller responsibility.
- Treat `main.py`, `parsers/`, `strategies/` and `policies/` as legacy archive
  candidates, not product runtime.
- Do not repair legacy bugs unless the code is being extracted into a target
  core or store adapter.
- Move more store-specific route and API markers into each store KB file as
  those stores are stabilized.
- Keep installer/update work out of the active code path until GUI MVP exists.

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q main.py models parsers policies strategies utils scripts tests
.\.venv\Scripts\python.exe scripts\architecture_check.py
```

## Manual Smoke Commands

Visual Pyaterochka check:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_pyaterochka_visual.ps1
```

Passive API discovery:

```powershell
.\.venv\Scripts\python.exe scripts\discover_pyaterochka_api.py --listen-seconds 180
```

## Later Roadmap

1. PyInstaller portable build.
2. Inno Setup installer.
3. GitHub Releases delivery flow.
4. One more real store after launcher MVP is stable.
5. Scheduler/background runs after multi-store stability.
6. Server/backend work only after the desktop product is genuinely useful.
