# ParserRIba Next Steps

Date: 2026-06-13

## Active Track

The active track is Launcher V3 and a clean core/layer architecture. The
canonical product path is:

`Исследование -> Каталог -> Товары -> Отчёт -> Профиль/История`

The project should move toward a clean program, not a pile of legacy parsers.
Obsolete code is removed only after imports and tests prove the active launcher
path no longer depends on it; git history is the long-term archive.

Work mode: local-first. Continue development, launcher runs and diagnostics in
`C:\tmp\ParserRIba-clean`. Use Git/GitHub only to commit, preserve history,
back up and review completed local slices.

Agent work mode: use `specs/013-local-agent-os/` and
`scripts/local_agent_os.py` for complex agent tasks that need an ISA note, RLM
trajectory and optional local Obsidian mirror. This is developer tooling only
and must not become ParserRIba runtime.

Codex RLM sidecar mode: use `specs/015-codex-rlm-sidecar/` and
`scripts/codex_rlm_sidecar.py` for upstream RLM experiments. It uses an isolated
sidecar environment and starts from a localhost-compatible endpoint. Product
runtime must not import `rlm` or `rlms`.

Protected-store manual gate mode: `specs/016-protected-manual-gate/` is the
current runtime stability slice for manual captcha/readiness handling. Catalog
discovery and Pyaterochka product collection should share
`utils/protected_store_manual_gate.py`; do not add a second manual wait loop in
store adapters.

## Immediate Priorities

0. Close the launcher information-architecture and theme spec:
   - completed implementation feature:
     `specs/012-launcher-information-architecture/`;
   - completed UX contract: the top strip is user-facing, the right context is
     route-specific, `Товары` owns selected-product detail in its route context
     and light/dark themes use modern neutral semantic tokens;
   - remaining launcher UX pain: the 960px visual review still shows cramped
     forms and horizontal workspace scrolling, so the next UX slice should
     focus on responsive layout rather than another status/context rewrite;
   - implementation rule for the next slice: preserve existing launcher
     controller/task/storage contracts and migrate one workspace at a time with
     focused tests and launcher smoke;
   - previous launcher UX baseline:
     `specs/007-launcher-ux-overhaul/` remains useful historical context, and
     `012` is now the current shell/context/theme contract;
   - related cleanup plan:
     `specs/006-workspace-cleanup/` keeps the working tree focused on active
     runtime, tests, specs and current docs;
   - completed architecture hardening: refreshed `graphify-out`, created
     `docs/ARCHITECTURE_HARDENING_AUDIT.md`, made launcher runtime statuses
     explicit, strengthened `architecture_check.py` and centralized launcher
     `wine_styles` compatibility in `launcher/desktop_filter_aliases.py`;
   - completed safe split workflow: split the pre-existing long `tests/test_desktop_filter_panel.py`
     file; `architecture_check.py` now reports no findings.
   - completed agent-ops workflow slice: `specs/009-agent-ops-workflow/`,
     `docs/AGENT_WORKFLOW.md` and `scripts/agent_ops_check.py` now define the
     local workflow for skill routing, Superpowers/spec-kit usage, guard-backed
     verification, subagent use and future project reuse.
   - visual review debt: `scripts/launcher_visual_review.py` can generate
     light/dark screenshots; the 1440px workspace/journal and dark scrollbar
     polish is addressed, but the 960px review still shows cramped forms and
     horizontal workspace scrolling that should be addressed in the next
     launcher UX slice.
   - visual review debt: the 960px research screen still clips the long URL
     placeholder; shorten helper text or move it out of the input in a focused
     launcher form-polish slice.
1. Stabilize the Pyaterochka end-to-end Launcher V3 flow:
   - completed protected-store manual gate unification:
     `specs/016-protected-manual-gate/` routes Pyaterochka product collection
     through the shared manual readiness gate used by catalog discovery;
   - research site/catalog;
   - select discovered catalog nodes;
   - collect products from selected node URLs;
   - show products in `state.products.items`;
   - filter the current product workspace locally;
   - select exact products;
   - choose report columns;
   - build Excel/JSON artifacts from selected or filtered products.
2. Improve product-card extraction:
   - preserve raw fields from API/listing/product cards;
   - normalize producer/manufacturer/supplier/vendor/brand;
   - extract country, weight, volume, fat, packaging, type, variants and
     category-like product subgroups when present;
   - continue expanding real payload aliases for sugar, color, package size,
     variants and other category-specific fields only through the shared
     raw-field extraction contract;
   - keep long text fields in product details, not as noisy filters.
3. Improve filter interpretation:
   - keep `FacetDescriptor` as the site-filter contract;
   - show only Russian user-facing filter titles;
   - separate mapped filters from site facets that cannot yet apply locally;
   - never split a site facet into technical UI filters such as `field_name`,
     `filter_type`, `range_min_val` or `list_values`.
4. Improve reports:
   - keep report columns selectable by the user;
   - user-selected columns take precedence over intent-specific templates;
   - save selected report-column sets later into the store profile;
   - export normalized fields and useful raw fields without falling back to
     obsolete fish/wine column assumptions.
5. Make `StoreProfile` central:
   - completed spec-kit feature `specs/003-workspace-favorites-themes/` added
     workspace favorites for stores, catalog nodes and products, one-action
     favorite refresh, full workspace profile selection, workspace-scoped
     preset reads and persistent light/dark launcher themes;
   - active spec-kit feature: `specs/002-project-workspace-profiles/` adds
     `ProjectWorkspace` above `StoreProfile`, so one user workspace can own
     many store profiles, saved sessions, artifacts, journals and future price
     history;
   - completed workspace foundation and first launcher workspace slice:
     default workspace creation/migration, workspace CRUD/list methods,
     workspace-scoped profile listing and a compact launcher workspace panel;
   - completed selected-session slice:
     workspace/profile-scoped session listing, fail-closed selected version
     loading and a compact saved-session list in the profile/session pane;
   - completed workspace journal slice:
     secret-safe journal writes for manual saves, session loads, missing-session
     attempts and launcher task completion/failure, plus a compact recent
     journal view in the workspace panel;
   - completed price-history comparison slice:
     workspace/profile-scoped price observations and latest-session comparison
     are visible as a compact summary in the profile/session pane;
   - one profile per site/domain;
   - store catalog snapshot, selected nodes, product workspace, filter sets,
     report columns, diagnostics and future price history separately per
     profile.
   - first storage slice exists in `utils/store_profile_repository.py` and
     persists the current Launcher V3 snapshot into SQLite-backed profile
     tables without changing the launcher-facing JSON contract.
   - completed launcher tasks now call this repository and keep the existing
     readable JSON snapshot as a compatibility artifact.
   - load-latest-session action now exists in the launcher and restores the
     latest StoreProfile snapshot from SQLite without starting the browser.
   - manual `Сохранить текущее состояние` action now writes the current session
     into the same JSON + SQLite StoreProfile storage and stays disabled until
     a profile exists.
   - selected filters and selected report columns are saved in dedicated
     SQLite preset tables and overlaid when the latest session is loaded.
   - completed workspace favorites and refresh slice: stores, catalog nodes and
     products can be saved as workspace favorites, and selected/all favorites
     can be refreshed with per-item diagnostics.
   - completed workspace profile selector slice: the profile/session panel
     lists profiles across the active workspace and loads selected profile
     snapshots without browser runtime.
   - completed theme slice: the launcher has persistent light/dark themes with
     centralized `launcher/desktop_theme.py` tokens.
   - let a user reopen the latest saved product workspace without reloading the
     site, then explicitly refresh catalog/products when they want new prices;
   - price observations are now written from saved product workspaces, and the
     storage core can compare two latest sessions for one profile inside one
     workspace;
6. Continue legacy cleanup in small verified slices:
   - do not repair legacy bugs for their own sake;
   - extract useful mechanics into target cores/adapters;
   - remove obsolete files only after `rg` and tests confirm safety.
7. Apply replacement discipline for every new feature:
   - name the old path and the new contract before coding;
   - switch active callers to the new path;
   - remove the replaced path or document the exact blocker and removal
     condition.
8. Finish full store-neutral unification before expanding browser count,
   profiles or new stores:
   - continue removing Pyaterochka/5ka defaults from shared roots and launcher
     defaults;
   - keep Pyaterochka behavior behind the store adapter and knowledge base;
   - make active store/profile selection the source of task, report, filter and
     artifact routing;
   - preserve unknown/new sites as `discovery_only` until real adapters exist.
   - completed first task-boundary slice: generic `store_catalog_export` now
     requires explicit `shop` and `intent`; Pyaterochka aliases remain
     compatibility-only; the shared store registry lazy-loads the Pyaterochka
     adapter.
   - completed second contract slice: `RunManifest`, `ExportSelection`,
     `OnboardingResult`, generic export/report CLIs and store backend lookup now
     require explicit intent.
   - completed third launcher-state slice: launcher selection starts without an
     intent; known runtime-ready profiles may provide a `default_intent` after
     site research, so Pyaterochka gets `fish_catalog` only from profile
     metadata.
   - completed fourth launcher-routing slice: desktop export/report/filter
     controller routing now uses generic runner fields instead of fish/wine
     runner branches; old fish/wine constructor parameters remain compatibility
     aliases.
   - completed fifth launcher-helper slice: task helper wrappers now expose
     Pyaterochka compatibility helpers with explicit `intent`; old fish/wine
     launcher helper names are thin aliases rather than active routing paths.
   - completed sixth local-task-registry slice: `list_local_tasks()` and CLI
     `--list` show active store-neutral tasks by default; old Pyaterochka task
     names remain runnable compatibility aliases and are visible only through an
     explicit compatibility listing.
   - completed seventh launcher-label slice: launcher-facing export fixtures
     and labels now use `store_catalog_export` as the active product export task
     name; Pyaterochka-named labels remain only for old compatibility manifests.
   - completed eighth product-classification slice: generic report/display
     modules now use `utils/product_classification.py` instead of importing
     wine-specific heuristics directly.
   - completed ninth wording slice: visible launcher/CLI labels now show
     `wine_styles` as subcategory/subtype while keeping compatibility keys for
     saved reports and manifests.
   - completed tenth filter-contract slice: launcher/report filter models now
     accept neutral `subcategories` while synchronizing legacy `wine_styles`,
     and generated filter counts publish both keys.
   - completed eleventh caller-migration slice: active launcher/report filter
     callers now read `subcategories`; `wine_styles` remains a generated and
     loadable compatibility key for saved data and old manifests.
   - completed twelfth filter-count normalization slice: launcher state readers
     map legacy `wine_styles` counts into neutral `subcategories`, and active
     filter widgets no longer need a `wine_styles` key.
   - completed thirteenth breakdown-contract slice: export/report summaries now
     publish neutral `product_breakdown` while keeping `wine_breakdown` as the
     old manifest compatibility key.
   - completed fourteenth breakdown-reader slice: launcher/task report-summary
     readers now populate `product_breakdown` from legacy `wine_breakdown` when
     loading old manifests.
   - keep old Pyaterochka task aliases and `wine_breakdown` compatibility keys
     until there is an explicit compatibility-removal decision.
   - next store-neutral slice: keep narrowing remaining compatibility-only
     `wine_styles` references only when a backward-compatible migration path is
     clear.

## Cleanup Priorities

Use `docs/WORKSPACE_CLEANUP_INVENTORY.md` and
`docs/ARCHITECTURE_HARDENING_AUDIT.md` before removing obsolete source files.
The cleanup direction is to keep the working tree focused on active runtime,
tests, specs and current docs; git history is the long-term archive.

Completed cleanup slices:

- Active interception diagnostics support now uses
  `utils/interception_diagnostics_snapshot.py` and
  `tests/test_interception_diagnostics_snapshot.py`.
- Obsolete tracked history and legacy source can be removed after current
  reference scans and validation prove no active dependency remains.

Local artifacts to keep out of Git and clean as needed:

- `.playwright-mcp/`
- `ParserRIba Launcher.lnk`
- `data/`
- `logs/`
- `profiles/`
- `build/`
- `dist/`
- `GeoLite2*.mmdb`
- `__pycache__/`
- `.pytest_cache/`

## Validation Commands

Run from `C:\tmp\ParserRIba-clean` after each code or cleanup slice:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q models utils scripts tests stores launcher
.\.venv\Scripts\python.exe scripts\architecture_check.py
.\.venv\Scripts\python.exe scripts\run_desktop_launcher.py --smoke
```

For documentation-only slices, at minimum run:

```powershell
.\.venv\Scripts\python.exe scripts\architecture_check.py
.\.venv\Scripts\python.exe scripts\generate_project_flow_map.py
```

## Deferred

- Installer and release packaging.
- Additional runtime-ready stores after Pyaterochka Launcher V3 is genuinely
  usable end to end.
- Browser runtime selection beyond the completed Camoufox contract slice:
  launcher runtime UI, StoreProfile runtime preferences, optional CloakBrowser
  backend and A/B browser smoke. See `docs/BROWSER_RUNTIME_STRATEGY.md` and
  `specs/001-browser-runtime-selection/`.
- Remote backend, scheduler, dashboard, Postgres and server workers.
- Paid scraping/captcha/cloud/LLM services.
