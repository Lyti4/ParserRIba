# ParserRIba Project State

Date: 2026-06-13

## Current Summary

ParserRIba is now a launcher-first local Windows desktop program. The old
CLI/parser stack is no longer the product runtime. Active code should use
launcher/task/core/store contracts instead of importing legacy files; removed
legacy code lives in git history, not the working tree.

The active user workflow is:

`Исследование -> Каталог -> Товары -> Отчёт`

The active architecture is:

`Launcher -> Task Orchestrator -> Browser/Discovery Core -> Store Adapter -> Product Core -> Filter Core -> Report Core -> Storage/Profile Core`

Pyaterochka remains the first runtime-ready store adapter because it preserves
the important protected-store mechanics: Camoufox launch stability, persistent
profile, RU proxy/GeoIP, human-like behavior, safe interception and anti-bot
diagnostics. These mechanics must stay behind the browser/store adapter
contracts and must not become a generic legacy parser dependency.

Read these files first in a new project session:

1. `AGENTS.md`
2. `docs/PROJECT_STATE.md`
3. `docs/NEXT_STEPS.md`
4. `docs/TARGET_ARCHITECTURE.md`
5. `docs/PROJECT_STRUCTURE.md`
6. `docs/DATA_FLOW_THREADING_PLAN.md`
7. `docs/PROJECT_FILE_FLOW_MAP.md`
8. `docs/TOOLS_POLICY.md`
9. `docs/AUTOMATIONS.md`
10. `docs/ARCHITECTURE_STEWARD.md`
11. `docs/WORKSPACE_CLEANUP_INVENTORY.md`

## Environment

- Primary workspace: `C:\tmp\ParserRIba-clean`
- Working mode: local-first. Code edits, launcher runs, profiles, SQLite,
  JSON/Excel artifacts and diagnostics are produced from this local workspace.
  Git/GitHub is used for commits, history, backup and review, not as the active
  runtime source.
- Python: `C:\Python311\python.exe`
- Virtual environment: `C:\tmp\ParserRIba-clean\.venv`
- Current branch: `codex/catalog-tree-discovery-core`
- Git remote for commit backup/review: `https://github.com/Lyti4/ParserRIba.git`
- Current focus: launcher UX overhaul, product workspace readability, dynamic
  filters, report column selection, profile/storage hardening, full
  store-neutral unification and cleanup planning.

## What Works

- PySide6 launcher starts through `scripts/run_desktop_launcher.py`.
- Launcher workflow uses four visible stages: `Исследование`, `Каталог`,
  `Товары`, `Отчёт`.
- Long launcher actions run through the background-action/task boundary instead
  of mutating Qt widgets from worker threads.
- `site_onboarding_discovery` performs store-neutral catalog discovery and
  returns discovery-only results for unknown sites instead of fake scaffolds.
- Catalog discovery can return full catalog links, normalized tree data,
  phase/progress state and partial warnings.
- The catalog tab supports checkbox multi-selection of discovered nodes.
- Product collection accepts selected catalog nodes with URLs and merges
  products into `LauncherAppState.products.items`.
- The `Товары` tab is the main product workspace: product table, product card,
  mini-catalog, selected-product state and embedded filter panel live there.
- Dynamic filters are derived from collected products, raw fields and
  site-provided facet descriptors where they can be mapped.
- Product-card raw field extraction now preserves additional detail fields such
  as sugar, sugar class, color, variant and package size when the site payload
  exposes them; those fields flow into filters and selectable report columns.
- Filter selections are visible in a selected-filter summary and apply locally
  to the current product workspace without deleting the original product list.
- Product mini-catalog derives subgroups such as product type/weight/fat from
  collected product names and raw data.
- Report export can use selected product IDs or the current filtered workspace.
- The `Товары` tab no longer needs a separate "select shown products" step:
  reports use explicit selected product IDs when present, otherwise the current
  filtered product table is the report scope.
- The `Товары` route now gives the product table primary workspace width and
  moves selected-product details into the route-specific right context instead
  of competing with a fixed global store/save summary.
- The report tab exposes selectable Excel columns based on base columns, raw
  product fields and discovered filter fields.
- User-selected report columns take precedence over intent-specific Excel
  templates, so selected products can be exported with the columns the user
  chose.
- Launcher profile snapshots now include explicit filter and report-column
  presets plus a compact workspace summary. These are the local JSON contract
  for the future central StoreProfile tables.
- `StoreProfileRepository` now provides the first central SQLite profile core:
  `store_profiles`, `profile_versions`, catalog/product workspace snapshots,
  filter/report presets and `price_observations`. It can save the current
  Launcher V3 snapshot and load the latest saved profile by shop/site.
- Workspace-scoped session history is now available through
  `list_profile_versions(workspace_id, profile_id)` and
  `get_profile_version(workspace_id, profile_id, version_id)`. The launcher can
  list saved sessions for the active profile and load a selected saved version
  without starting browser runtime.
- Workspace activity journal is active in SQLite and launcher UI. Manual saves,
  session loads, missing-session attempts and completed/failed launcher tasks
  write secret-safe journal events scoped by workspace.
- Price-history comparison is workspace/profile scoped in storage. The compact
  right-side store summary no longer shows price-history internals; that data
  belongs in a dedicated price-history surface.
- Completed spec-kit feature `specs/003-workspace-favorites-themes/` added
  workspace favorites for stores, catalog nodes and products, one-action
  favorite refresh, full workspace profile selection, workspace-scoped preset
  reads and persistent light/dark launcher themes.
- Completed spec-kit feature `specs/004-architecture-hardening-code-quality/`
  added graphify-backed architecture audit, honest runtime status contracts,
  store-neutral shared roots, automated guardrails and maintainability cleanup
  slices.
- Completed spec-kit feature `specs/005-safe-file-split-workflow/` added the
  local safe file split workflow and split the long desktop filter panel test.
- Spec-kit feature `specs/006-workspace-cleanup/` defines and executes the
  cleanup plan for removing stale legacy/history references after graphify,
  `rg`, git-state and validation evidence prove they are not active runtime
  dependencies.
- Spec-kit feature `specs/009-agent-ops-workflow/` defines the local agent
  workflow for ParserRIba and future projects: current-doc startup, skill
  routing, Superpowers/spec-kit usage, subagent routing, guard-backed
  verification and handoff discipline.
- Spec-kit feature `specs/013-local-agent-os/` adds the local agent workflow
  surface for ISA notes, RLM execution traces, optional Obsidian mirroring and
  secret-safe containment. It is developer tooling only, not product runtime.
- Completed spec-kit feature `specs/016-protected-manual-gate/` unifies
  protected-store manual challenge readiness for catalog discovery and
  Pyaterochka product collection through the shared manual gate. Product
  collection no longer owns a separate polling loop and can keep the longer
  operator wait window without sending repeated browse rounds during captcha
  solving.
- `docs/AGENT_WORKFLOW.md` is now the main process guide for agent workflow,
  and `scripts/agent_ops_check.py` runs the lightweight guard set for changed,
  staged or all tracked surfaces.
- Completed spec-kit feature `specs/012-launcher-information-architecture/`
  redesigned the launcher shell around a short user-facing top status,
  route-specific right context, owned product details for `Товары` and modern
  neutral light/dark theme tokens.
- Architecture hardening now has `docs/ARCHITECTURE_HARDENING_AUDIT.md`,
  explicit launcher manifest-status mapping, stronger architecture guardrails
  and centralized launcher filter alias compatibility in
  `launcher/desktop_filter_aliases.py`.
- The launcher now has a workspace profile selector in the profile/session
  pane. Switching profiles loads the selected workspace/profile snapshot,
  sessions and presets from local SQLite without starting browser runtime.
- The launcher has persistent light/dark theme selection backed by
  centralized modern semantic tokens in `launcher/desktop_theme.py` and local
  launcher settings.
- The launcher already has V4 shell building blocks (`desktop_workspace_shell`,
  `desktop_navigation`, `desktop_command_strip`, `desktop_inspector_panel`).
  The current remaining UX debt is mostly responsive layout at 960px, where
  some forms still become cramped and the workspace can require horizontal
  scrolling.
- Latest-session loading now overlays selected filters and report columns from
  the dedicated `filter_presets` and `report_presets` tables, not only from the
  raw profile-version JSON payload.
- Saving a StoreProfile product workspace now records `price_observations`, and
  the storage core can compare product prices between the latest two saved
  sessions for one profile.
- Completed launcher tasks now persist profile state in two forms: the existing
  readable JSON snapshot under `data/launcher_profiles/` and the central SQLite
  database at `data/profiles/store_profiles.db`.
- The launcher can load the latest saved StoreProfile session from SQLite back
  into `state.profile`, `state.catalog`, `state.products`, filters, report
  columns and selection without starting Camoufox or a local task subprocess.
- The `Магазин и сохранения` pane can manually save the current StoreProfile
  state and keeps that action disabled until a profile exists.
- Generic product Excel output is available through
  `utils/generic_excel_report.py` and routed by `utils/report_excel_router.py`;
  the old wine-specific report shape is no longer the only output path.
- Local task/actor contracts exist for discovery, product export, report export
  and report/filter support.
- Generic `store_catalog_export` now requires explicit `shop` and `intent` at
  the task boundary, so a missing profile selection cannot silently fall back to
  Pyaterochka/fish export. Pyaterochka task names remain only as compatibility
  aliases.
- Local task listing now hides compatibility aliases by default. Old
  `pyaterochka_catalog_export`, `pyaterochka_fish_export` and
  `pyaterochka_wine_export` task names can still run through `run_local_task()`
  and the CLI compatibility list, but they are not advertised as active tasks.
- Task/report/onboarding result contracts now require explicit `intent`; generic
  export/report CLI entrypoints also require `--intent`.
- Launcher selection now starts with an empty intent. Known runtime-ready store
  profiles can provide a `default_intent` after site research; Pyaterochka
  resolves to `fish_catalog` only from known-store metadata, not from generic
  launcher defaults.
- Desktop launcher export/report/filter orchestration now uses generic
  `store_export_runner`, `report_runner` and `filter_options_runner` fields.
  Fish/wine-named runner parameters are compatibility aliases, not active
  routing branches.
- Launcher task helper wrappers now expose Pyaterochka compatibility helpers
  with explicit `intent`. Fish/wine-named launcher helper functions are thin
  aliases only; active launcher routing uses generic store/report task paths.
- Launcher-facing product export fixtures and task labels now use
  `store_catalog_export` as the active task name. Pyaterochka-named labels stay
  only to render old compatibility manifests and saved snapshots cleanly.
- Generic launcher/report display modules now import product classification
  through `utils/product_classification.py`. Current wine heuristics remain
  available behind that neutral facade and inside the Pyaterochka adapter.
- `utils/store_catalog_registry.py` builds the Pyaterochka export backend lazily,
  so importing the shared registry no longer imports the Pyaterochka adapter
  modules immediately.
- A browser-runtime contract exists for discovery with Camoufox as the stable
  default backend. Further second-browser work is deferred until store-neutral
  unification is complete enough to avoid adding support surface too early.
- SQLite product storage and JSON/Excel artifacts remain local v1 storage.
- Architecture check is expected to pass with the known long-file warning for
  `tests/test_desktop_filter_panel.py`.

## Current Limitations

- The product-card extraction still needs richer real-site payload coverage for
  some categories. If only category/brand is present, the UI correctly has few
  filters.
- Site-provided facets are normalized, but only locally mapped filters can
  narrow already collected products. Unmapped site filters need a later
  browser/API re-query layer.
- Profile storage has a central SQLite core, launcher task persistence,
  workspace-scoped profile/session listing, selected-session loading,
  manual-save actions, workspace journal events, price-history comparison and
  explicit workspace/profile-scoped preset table loading.
- Catalog trees for some sites are still shallow when the site exposes a flat
  category list or hides substructure behind listing payloads.
- Legacy `main.py`, old parser/policy/strategy code, `utils/site_probe.py` and
  the old `utils/session_manager*` pair are not active runtime. Removed legacy
  source belongs in git history rather than a tracked working-tree archive.
- User-facing documentation still needs a broader release-readiness pass before
  packaging, but the Windows quickstart now points to the launcher-first path.
- Browser runtime selection is paused after the initial Camoufox contract slice.
  Launcher runtime switching, StoreProfile runtime preferences and optional
  CloakBrowser support should wait until shared roots are store-neutral.
- Remaining `fish_catalog` references are intent implementation, Pyaterochka
  compatibility wrappers, labels for old manifests, tests and diagnostics.
  Visible launcher/CLI wording now treats `wine_styles` as product
  subcategory/subtype. Launcher/report filter models now accept neutral
  `subcategories`, active launcher/report filter callers read that neutral
  field, and launcher filter-count readers map old `wine_styles` counts into
  `subcategories`. The legacy `wine_styles` alias stays synchronized for saved
  reports and manifests. Export/report summaries now publish neutral
  `product_breakdown`, and launcher/task readers populate it from old
  `wine_breakdown` summaries when loading legacy manifests. Old
  `wine_breakdown` keys remain compatibility contracts until a separate
  migration/removal decision.
- Packaging, installer, update delivery, remote backend and multi-store
  production rollout are not active priorities.

## Safety Notes

- Do not commit `.env`, proxy strings, cookies, captcha tokens, auth headers,
  browser profiles, generated reports, mmdb databases, logs, `data/`, `build/`
  or `dist/`.
- Do not integrate paid browser APIs, paid captcha solving, cloud scraping or
  LLM services without explicit user approval.
- Runtime remains local Python + Camoufox + SQLite/JSON/Excel.
- Playwright/Chrome DevTools/browser tooling is diagnostic-only unless promoted
  by an explicit architecture decision.
