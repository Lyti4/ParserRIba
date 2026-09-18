# ParserRIba Product/Application Wayfinder Plan

**Date:** 2026-08-08
**Status:** Gate 0 approved; Gate 1 factual baseline completed; P0-A implementation not authorized; `D-17` Herdr lifecycle/no-tool route accepted, native tools blocked below Herdr
**Repository:** `/home/hermesadmin/work/ParserRIba-clean`
**Baseline:** branch `codex/catalog-tree-discovery-core`, HEAD `7384328602249888d80f5a4631a4730d201ad4cc`
**Gate 1 worktree:** `/home/hermesadmin/work/ParserRIba-worktrees/p0-application-workflow`, branch `codex/p0-application-workflow`, HEAD `7384328602249888d80f5a4631a4730d201ad4cc`
**Gate 1 evidence:** `/home/hermesadmin/out/parserriba-gate1-20260808/cli-runmanifest-contract-baseline.md`, SHA-256 `e25a3365b1c2455bd0ac7beb20fd34dd3bc5dc7f269c4e644eb1e8823639cf43`
**Scope:** product/application architecture, launcher information architecture, data ownership, delivery map and acceptance gates
**Not authorized by this document:** implementation, install, live retailer run, runtime switch, commit, push, release or publication

## 0. How to read this plan

Labels used throughout:

- **Existing** — verified in the current repository.
- **Refactor target** — existing behavior/data remains supported but its ownership or placement should be tightened.
- **Proposed** — recommended design, not a current contract.
- **Future gate** — intentionally deferred until a named trigger and Product Owner decision exist.

This is a Wayfinder map: it defines the destination, decisions, dependency order and completion evidence. It is not a license to implement every item. Each implementation milestone requires its own approved isolated worktree, bounded spec and acceptance gate.

This document is the single Gate-0-approved master planning surface for ParserRIba product/application architecture and delivery. Within this planning cycle, prior architecture, IA, research and next-step documents are subordinate evidence; when they conflict, this document owns the approved Gate 0 direction until a later explicitly superseding decision record or master plan replaces it. Known baseline conflicts remain reconciliation work rather than silently accepted truth.

## 1. Evidence and independent lanes

### 1.1 Repository evidence inspected

- `AGENTS.md`
- `docs/PROJECT_STATE.md`
- `docs/NEXT_STEPS.md`
- `docs/TARGET_ARCHITECTURE.md`
- `docs/DATA_FLOW_THREADING_PLAN.md`
- `docs/DECISIONS.md`
- `docs/LAUNCHER_ARCHITECTURE_RESEARCH_20260808.md`
- `specs/002-project-workspace-profiles/data-model.md`
- `specs/012-launcher-information-architecture/spec.md`
- `specs/012-launcher-information-architecture/data-model.md`
- `launcher/desktop_navigation.py`
- `launcher/desktop_workflow_tabs.py`
- `launcher/desktop_command_strip.py`
- `launcher/desktop_inspector_panel.py`
- `launcher/desktop_project_workspace.py`
- `models/launcher_state.py`
- `utils/site_onboarding.py`
- `utils/local_task_registry.py`
- `utils/store_export_runtime.py`
- `utils/pyaterochka_runtime.py`
- `utils/store_profile_schema.py`
- `utils/product_storage.py`

### 1.2 Methods

- Matt workflows: `matt-router`, `wayfinder`, `domain-modeling`, `codebase-design` routing, `writing-for-agents` briefing discipline.
- Claude lane through Herdr: Claude Sonnet 5, effort `high`, plan mode, only `Read/Glob/Grep`, Chrome/MCP disabled.
- Codex lane through Herdr: `gpt-5.6-sol`, effort `high`, Codex App Server, Headroom route, read-only, Hermes tools and Telegram environment disabled.
- Independent review through Herdr: Claude Opus 5, effort `max`, two packet-based Matt axes (`code-review` WIP overlay + `codebase-design`; `code-review` WIP overlay + `wayfinder`), tools/MCP disabled. The review was bound to pre-repair SHA-256 `097bfa8362a5ac223edb01530ebd677f297e9327192a360e84c7d348378b61a4`; this document-only pass applies the adjudicated findings, followed by deterministic verification rather than a second model review.
- Hermes owns adjudication, repository evidence, validation and the final plan.

### 1.3 Known baseline conflicts

1. `specs/012-launcher-information-architecture/spec.md` still declares `Draft`, while `docs/PROJECT_STATE.md` calls feature 012 completed.
2. Navigation rail order and hidden `QTabWidget` order are maintained separately; `proxy` and `diagnostics` use different positions in the two lists.
3. `profile` is disabled as a route, although profile/session controls already exist in the workspace and right inspector.
4. Product/price data is duplicated across central StoreProfile storage and `ProductStorage` tables.
5. Current status vocabularies do not express blocked/manual/partial/cancelled outcomes consistently.
6. Build script and PyInstaller spec do not freeze one packaging truth.

These are baseline reconciliation tasks, not permission for broad cleanup.

---

# 2. Destination

## 2.1 Product destination

ParserRIba becomes a reliable local-first product for monitoring store catalogs, product availability and prices, with one understandable user flow:

```text
ProjectWorkspace
→ StoreProfile
→ ResearchRun
→ CatalogSnapshot
→ explicit catalog selection
→ product collection
→ ProductWorkspace
→ local filtering and product selection
→ ReportRun / artifacts
→ ProfileVersion + PriceSnapshot
→ comparison on the next run
```

The first accepted commercial proof is deliberately narrow:

1. one paying user or clearly identified buyer;
2. one recurring report definition;
3. one reliable Pyaterochka workflow;
4. one accepted browser/runtime configuration;
5. one launcher/application architecture;
6. one Windows clean-machine acceptance path.

## 2.2 Architectural destination

```text
PySide6 Qt Widgets GUI ─┐
                       ├── ApplicationWorkflow / application services
CLI / automation ──────┘          │
                                  ├── commands
                                  ├── queries
                                  ├── immutable progress/events
                                  ├── terminal result
                                  ├── repositories
                                  │
                                  ├── central local SQLite
                                  └── single owned worker boundary
                                           │
                                           ├── browser/discovery core
                                           ├── store adapter
                                           └── serializable result/artifacts
```

Hard invariants:

- GUI, CLI and future platform adapters do not own independent business logic.
- Qt objects exist only in the GUI thread.
- Browser/runtime workers do not mutate Qt state.
- P0 has one task owner, one browser owner, one browser profile, one trace directory and one terminal result.
- The target is one central product SQLite source of truth; the current multi-file baseline remains explicit in section 6.0 until migration gates are passed.
- JSON/Excel/CSV/PDF/export SQLite are artifacts or compatibility snapshots.
- Secrets never enter product SQLite, journal events, reports or support bundles.
- Empty, blocked or manual-action results are not reported as success.
- Only `ready` may project to ordinary `succeeded`; every non-ready terminal outcome remains visibly non-successful on legacy surfaces.
- Cancellation is cooperative in P0; forced worker termination is not a P0 behavior.
- CAPTCHA, WAF and login challenges are never bypassed in any phase; the workflow stops with an explicit human-resolved manual gate.

## 2.3 Non-goals for P0

- cloud backend or Postgres;
- mobile extraction runtime;
- second production store adapter;
- second production browser runtime;
- per-user supervisor/service or named-pipe infrastructure;
- unattended scheduler execution;
- framework rewrite;
- updater/signing system before the product workflow is accepted;
- automatic migration of proxy credentials or browser profiles.

## 2.4 Users and jobs-to-be-done

These are product roles, not access-control roles.

| User/job | Primary outcome | Launcher path |
|---|---|---|
| **Operator / analyst** | Configure one store context, run collection safely, handle an explicit manual gate and obtain a usable dataset | Research → Catalog → Products → Report |
| **Category manager / buyer** | Receive the same recurring report, understand price/availability changes and act on important products | Report → Price history → Favorites |
| **Product Owner / support operator** | Approve profiles and versions, diagnose failures, protect credentials and validate releases | Profile → Diagnostics → Proxy; future Stores/Scheduler |

The P0 design optimizes for the first role while producing an artifact useful to the second. The third role owns human gates; it is not replaced by automation.

---

# 3. Launcher information architecture

## 3.1 Shell

Keep the existing V4 shell as the incumbent-first base. Proposed additions are labelled rather than presented as current implementation:

```text
┌─────────────────────────────────────────────────────────────────────┐
│ Application menu (Proposed P1)                                      │
├─────────────────────────────────────────────────────────────────────┤
│ Command strip: store · state · progress · counts · artifact · next │
├──────────────┬──────────────────────────────────────┬───────────────┤
│ Navigation   │ Active route workspace               │ Right         │
│ rail         │                                      │ inspector     │
│              │                                      │               │
├──────────────┴──────────────────────────────────────┴───────────────┤
│ Optional compact status/cancellation surface during active run      │
└─────────────────────────────────────────────────────────────────────┘
```

### Shell ownership

| Surface | Ownership | Rule |
|---|---|---|
| Application menu (Proposed P1) | launcher adapter | System-level actions only; no product workflow duplication |
| Navigation rail | launcher adapter | Product workspaces/routes only |
| Command strip | launcher read model | One concise state line; no raw IDs or technical enums |
| Route workspace | route-specific presenter | Owns the main task and its primary controls |
| Right inspector | route-specific presenter | Context/details, not a second competing workspace |
| Cancellation/status | application workflow projection | Same run state as CLI |

## 3.2 Navigation rail decision

### Release routes

1. **Исследование** — Existing, P0.
2. **Каталог** — Existing, P0.
3. **Товары** — Existing, P0.
4. **Отчёт** — Existing, P0.
5. **Профиль** — Refactor target, activate in P1 by regrouping existing profile/session behavior.
6. **История цен** — Proposed, activate in P1/P2 after canonical price lineage is accepted.
7. **Избранное** — Existing, P0.
8. **Диагностика** — Existing, strengthen in P0/P1.
9. **Прокси** — Existing, strengthen in P1; keep secrets outside SQLite.

### Deferred routes

10. **Магазины** — Future gate. It must mean adapter/capability management, not duplicate `Профиль`.
11. **Планировщик** — Future gate. Keep disabled until unattended ownership, recovery and Windows lifecycle are accepted.

### Rail order

Recommended order:

```text
Работа
  Исследование
  Каталог
  Товары
  Отчёт

Данные
  Профиль
  История цен
  Избранное

Система
  Диагностика
  Прокси

Будущее / disabled
  Магазины
  Планировщик
```

The implementation must derive rail order and route-to-view mapping from one registry. Do not maintain independent `NAV_ITEMS` and tab-order truths without a deterministic mapping test.

## 3.3 Application menu

The menu is for application-level actions; it must not become a second navigation rail.

| Menu | Item | Status | Action/command | Gate |
|---|---|---|---|---|
| **Файл** | Новое рабочее пространство | Proposed P1 | `CreateWorkspace` | Validate non-empty name; no secrets |
| | Открыть рабочее пространство | Proposed P1 | `ActivateWorkspace` | No browser start |
| | Резервная копия | Proposed P2 | `CreateWorkspaceBackup` | WAL checkpoint, manifest and checksum |
| | Восстановить копию | Proposed P2 | `ValidateBackup` then `RestoreWorkspaceBackup` | Explicit confirmation; pre-restore backup |
| | Открыть папку отчётов | Existing action, regroup | OS adapter | Missing path is non-fatal |
| | Открыть папку данных | Proposed P1 | OS adapter | Never expose secret/browser-profile folders |
| | Выход | Proposed menu placement | `RequestApplicationExit` | P0 uses cooperative cancel/wait; force is a separately approved future policy (`D-15`) |
| **Вид** | Тёмная тема | Existing, regroup | launcher setting | No DB profile mutation |
| | Светлая тема | Existing, regroup | launcher setting | No DB profile mutation |
| | Системная тема | Future gate | launcher setting | Only after visual acceptance |
| | Сбросить компоновку | Proposed P1 | launcher adapter | Does not reset product data |
| **Инструменты** | Проверить среду | Proposed P0/P1 | `RunDoctor` | Read-only diagnostics |
| | Проверить browser runtime | Proposed P0/P1 | `RunBrowserCheck` | No retailer request unless separately approved |
| | Проверить прокси | Existing, refactor | `TestProxy` background action | Redacted output; no GUI blocking |
| | Экспорт диагностики | Proposed P1 | `CreateRedactedSupportBundle` | Secret scan before final artifact |
| | Настройки | Refactor target P1 | open settings dialog | Advanced runtime options leave Research route gradually |
| **Справка** | Руководство | Proposed P2 | open packaged local docs | No network dependency |
| | Данные и приватность | Proposed P2 | open local policy | Explain storage and secret boundaries |
| | О программе | Proposed P1/P2 | version/build/runtime summary | No credential/provider details |

Not in the menu:

- Collect products, generate reports, save filters, refresh favorites and cancel a run remain route actions.
- Profile selection remains in the `Профиль` route and compact global context, not duplicated as a menu tree.

## 3.4 Command strip contract

### Always visible

- active store/profile display name;
- task status in clear Russian;
- current progress when a run is active;
- product counts: collected / visible / selected;
- latest artifact display name when available;
- one recommended next action;
- cancel action only when the current run supports cancellation.

### Never shown in normal state

- raw profile/version/run IDs;
- internal task keys;
- browser credentials;
- proxy URLs with authentication;
- cookies, headers or challenge tokens;
- raw Python exceptions.

## 3.5 Right inspector policy

| Route | Inspector content |
|---|---|
| Исследование | active profile/session summary, last saved version, manual-action instructions |
| Каталог | selected-node summary, snapshot provenance, collect readiness |
| Товары | selected product card/details; no duplicated profile summary |
| Отчёт | report scope, selected columns count, latest artifact |
| Профиль | compact version provenance or nothing; main profile workspace owns the content |
| История цен | selected product/change details and two compared snapshots |
| Избранное | selected favorite details and refresh capability |
| Диагностика | selected failure/check details and reproduction |
| Прокси | masked endpoint/test summary; never raw credentials |
| Магазины | adapter capability details if route is activated |
| Планировщик | selected schedule/run details if route is activated |

Rule: if the route workspace already owns the full object, the inspector must not duplicate it.

---

# 4. Route-by-route plan

For every route the same design chain applies:

```text
user intent
→ visible actions
→ application command/query
→ owning module/aggregate
→ tables read/written
→ events/outcome
→ gate and diagnostics
→ acceptance evidence
```

## 4.1 Исследование

**Status:** Existing; P0 vertical-flow owner.

### User intent

Create or refresh knowledge about one store site and obtain a trustworthy catalog snapshot.

### Main workspace

- store URL and active profile;
- simple mode selector: step-by-step or final result;
- primary action: `Начать исследование` / `Повторить исследование`;
- progress phases in Russian;
- explicit manual-action card when the site requires operator attention;
- final summary: found nodes, warnings, profile state and next action.

Advanced runtime/headless/manual-wait/attempt settings remain visible for compatibility in P0, then move into Settings after the settings dialog is accepted.

### Commands and queries

- **Existing adapter:** current `site_onboarding_discovery` path.
- **Proposed command:** `StartResearch(workspace_id, profile_id?, site_url, options)`.
- **Proposed command:** `CancelRun(run_id)`.
- **Proposed query:** `GetResearchRun(run_id)`.
- **Proposed query:** `ListRunEvents(run_id, after_sequence)`.

### Ownership and data

- Aggregate: `StoreProfile` + `ResearchRun`.
- Reads: `project_workspaces`, `store_profiles`, `profile_versions`.
- Writes: `workflow_runs`/events when introduced, `profile_versions`, `catalog_snapshots`, `workspace_journal_events`.
- P1 projection: `catalog_nodes`.
- Secrets/browser profiles: external references only.

### Events and terminal outcomes

- `ResearchStarted`
- `ResearchPhaseChanged`
- `CatalogEvidenceFound`
- `ManualActionRequired`
- `CatalogSnapshotCommitted`
- `RunTerminal`

Allowed terminal outcomes: `ready`, `blocked`, `manual_action_required`, `partial`, `failed`, and proposed `cancelled` after approval.

### Acceptance

- deterministic fixture creates the same normalized catalog snapshot and event sequence;
- browser worker never receives Qt objects;
- GUI remains responsive;
- manual gate does not repeat browse rounds automatically;
- blocked/empty output is not success;
- cancellation releases browser ownership and records one terminal result;
- no secret-bearing values appear in DB/events/logs.

## 4.2 Каталог

**Status:** Existing; P0.

### User intent

Inspect the discovered catalog, find required sections and explicitly choose nodes for product collection.

### Main workspace

- searchable hierarchical tree;
- node name, URL, child count and availability/provenance;
- actions: expand/collapse, select visible/all, clear selection;
- selected-node summary;
- primary action: `Собрать товары`;
- no implicit default category.

### Commands and queries

- `GetCatalogSnapshot(snapshot_id)`
- `SearchCatalogNodes(snapshot_id, text)`
- `ReplaceCatalogSelection(snapshot_id, node_ids)`
- `CollectProducts(profile_id, snapshot_id, selected_node_ids)`
- compatibility adapter to current `store_catalog_export`.

### Ownership and data

- Aggregate: immutable `CatalogSnapshot`; selection belongs to the active workspace/session.
- Existing: `catalog_snapshots.catalog_json`, `selected_nodes_json`.
- P1 projection: `catalog_nodes`, `catalog_selections`.
- Collection creates or refreshes a `ProductWorkspace`.

### Events and terminal outcomes

- selection changed;
- collection started/progressed/terminal;
- terminal outcome is `ready|partial|blocked|manual_action_required|failed|cancelled*`;
- `cancelled*` remains proposed until `D-14` freezes compatibility semantics.

### Acceptance

- selected node URLs reach collection unchanged;
- several selected nodes merge without replacing prior results;
- empty selection fails before browser start;
- search/filter does not modify the snapshot;
- projection rebuild matches snapshot content.

## 4.3 Товары

**Status:** Existing; P0, with P1 data normalization.

### User intent

Explore collected products, filter locally, inspect details and define the exact report scope.

### Main workspace

- left filter area with price, stock and dynamic fields;
- mini-catalog/type grouping;
- primary product table;
- explicit row/product selection;
- selected product details in the right inspector;
- actions: reset filters, show all, save filter preset, save checkpoint.

### Commands and queries

- `GetProductWorkspace(workspace_uid)`
- `FilterProductWorkspace(workspace_uid, filter_spec: FilterSpecV1)` — pure query/read-model operation.
- `SetSelectedProducts(workspace_uid, product_uids)`
- `SaveFilterPreset(workspace_id, profile_id, definition)`
- `CreateProductWorkspaceCheckpoint(workspace_uid)`

`FilterSpecV1` is a versioned P0-A value object. Its contract freezes strict-missing behavior, numeric/price normalization, Russian-text collation, stable ordering and tie-breaks, and validation/error outcomes before GUI/CLI equivalence is accepted.

### Ownership and data

- Existing: `product_workspace_snapshots`, `filter_presets`, launcher state.
- P1: `product_identities`, `product_observations`, `product_workspaces`, `product_workspace_items`.
- `products` in `ProductStorage` is not allowed to remain a second long-term source of truth.
- Filtering never deletes collected products.

### Acceptance

- filters derive from real collected fields;
- missing fields remain honest and support strict-missing behavior;
- reset restores the full workspace;
- GUI and CLI filter queries return the same ordered product-ID sequence under the same `FilterSpecV1`;
- product identity deduplication never auto-merges ambiguous items;
- 960×760 and 1440×900 layouts preserve a usable product table and one detail surface.

## 4.4 Отчёт

**Status:** Existing; P0.

### User intent

Choose output columns and build a reproducible report from selected or currently filtered products.

### Main workspace

- report scope summary;
- selected/filtered/collected precedence shown explicitly;
- selectable columns and saved report presets;
- preview;
- actions: select all/clear columns, build Excel, open file, open folder;
- artifact status and missing-file handling.

### Commands and queries

- `GetReportScope(product_workspace_uid)`
- `ListReportPresets(workspace_id, profile_id)`
- `SaveReportPreset(...)`
- `GenerateReport(product_workspace_checkpoint_uid, preset_version_uid, format)`
- `ListReportRuns(profile_id)`
- `GetArtifact(artifact_uid)`

### Ownership and data

- Existing: `report_presets`, profile snapshot artifact refs.
- P1: `report_runs`, `artifacts` registry.
- Report input references immutable profile/workspace/preset versions.
- Generated Excel/JSON remains outside SQLite; registry stores relative path, type, size, checksum and lineage.

### Acceptance

- explicit selection wins over filtered workspace;
- report can be reproduced from the same immutable references;
- user-selected columns win over templates;
- missing/open/locked files produce clear non-destructive errors;
- artifacts contain no secrets and are registered only after successful write.

## 4.5 Профиль

**Status:** Existing behavior, Refactor target; activate as a route in P1.

### Product meaning

`Профиль` manages user-owned store context and saved versions. It is not an adapter marketplace.

### Main workspace

- active `ProjectWorkspace`;
- profile list inside that workspace;
- profile summary: site, domain, runtime readiness, last update;
- saved versions/sessions timeline;
- actions: create profile from researched site, rename, open version, save current version, duplicate into another workspace if later approved, archive;
- no destructive delete in the first release.

### Commands and queries

- `ListWorkspaces`
- `ListProfiles(workspace_id)`
- `ListProfileVersions(profile_id)`
- `OpenProfileVersion(profile_id, version_id)`
- `SaveProfileVersion(profile_id, source_run_id, snapshot)`
- `RenameProfile`
- `ArchiveProfile` — Proposed; safer than immediate deletion.

### Ownership and data

- `project_workspaces`
- `store_profiles`
- `profile_versions`
- linked catalog/product snapshots, presets, observations, artifacts and journal events.

### Acceptance

- versions cannot be loaded across workspace boundaries;
- opening a saved version starts no browser;
- current catalog/products/filters/report columns restore together;
- archived profiles remain referentially valid for reports/history;
- no profile setting stores proxy/cookie/auth secrets.

## 4.6 История цен

**Status:** backend evidence exists; Proposed dedicated route after price lineage P1.

### User intent

Compare two accepted observations/snapshots and see price and availability changes with reproducible provenance.

### Main workspace

- profile and time-range selector;
- choose two snapshots or latest versus previous;
- summary cards: increased, decreased, new, missing, availability changed;
- change table;
- selected product history in inspector;
- export comparison report.

### Commands and queries

- `ListPriceSnapshots(profile_id)`
- `ComparePriceSnapshots(previous_uid, current_uid, filter_spec)`
- `GetProductPriceHistory(product_uid)`
- `ExportPriceComparison(...)`

### Ownership and data

- Existing: `price_observations`.
- P1: canonical product linkage and `price_snapshots` grouping.
- Price changes are initially computed as a query/view; a materialized `price_changes` table is added only if measured performance requires it.
- Existing `price_history` becomes read-only after reconciled migration.

### Acceptance

- no cross-profile comparisons;
- currency mismatch, missing product and unavailable product are distinct states;
- duplicate observations are idempotent;
- comparison includes source run/snapshot IDs internally and clear human labels externally;
- query does not load every raw JSON snapshot into memory.

## 4.7 Избранное

**Status:** Existing; P0.

### User intent

Save important stores, catalog nodes and products and refresh supported targets intentionally.

### Main workspace

- tabs or grouped list: stores / sections / products;
- refresh capability and latest result;
- actions: add current target, refresh selected, refresh all supported, remove from favorites;
- unsupported refresh remains visible with a reason.

### Commands and queries

- current favorites controller compatibility actions;
- proposed `ListFavorites`, `AddFavorite`, `RemoveFavorite`, `RefreshFavorites`, `CancelRun`.

### Ownership and data

- `workspace_favorites`
- `favorite_refresh_runs`
- `favorite_refresh_results`
- P1 linkage to canonical product/catalog identities.

### Acceptance

- favorites never fall back to a default store;
- refresh uses the owning profile and adapter capability;
- repeated refresh is idempotent;
- partial/unsupported results are not success;
- credentials are not copied into favorite payloads.

## 4.8 Диагностика

**Status:** Existing; strengthen in P0/P1.

### User intent

Understand what failed, what can be fixed and what safe evidence can be shared.

### Main workspace

- environment checks;
- dependency/browser check;
- current/previous run list;
- redacted errors and event timeline;
- artifact integrity;
- reproduction command with secrets omitted;
- actions: copy safe summary, export redacted bundle, open logs folder.

### Commands and queries

- `RunDoctor`
- `RunBrowserCheck(runtime)`
- `GetRun(run_id)`
- `ListRunEvents(run_id)`
- `VerifyArtifacts`
- `CreateRedactedSupportBundle(run_id?)`

### Ownership and data

- `workflow_runs`, `workflow_run_events`, `workspace_journal_events`;
- migration metadata and issues;
- `artifacts` registry when introduced;
- diagnostic bundle is an artifact, not another source-of-truth table.

### Acceptance

- explicit tests for proxy/token/cookie/header/password redaction;
- bundle excludes `.env`, browser profiles, cookies and unrelated messages/files;
- doctor is deterministic and read-only;
- failed checks return reason codes and remediation, not only prose;
- support bundle passes a secret scan before registration.

## 4.9 Прокси

**Status:** Existing; P1 safety/threading refactor.

### User intent

Configure and test an approved proxy route for protected-store work.

### Main workspace

- enable/disable;
- protocol;
- masked endpoint list;
- replace local configuration;
- test selected/first endpoint;
- latest test result, latency, external country/IP only when safe;
- no retailer request as part of a generic proxy test.

### Commands and queries

- `GetProxyConfigurationSummary`
- `ReplaceProxyConfiguration`
- `TestProxy`
- `GetLatestProxyTest`

### Ownership and data

- P0 Existing: local `.env`/environment ownership remains for compatibility.
- Product SQLite stores no credential values.
- P2 proposal: OS secure store with opaque `credential_ref`, only after a separate Windows security/packaging gate.
- Optional P1/P2 history: redacted `proxy_test_runs/results` or generic workflow runs.

### Acceptance

- test runs off the GUI thread;
- credentials are masked in UI/errors/events;
- disabling proxy does not delete credentials silently;
- unavailable secure store fails closed; never falls back to plaintext SQLite;
- no automatic paid proxy purchase or account change.

## 4.10 Магазины

**Status:** Future gate; disabled.

### Product meaning

If activated, `Магазины` is the adapter/capability registry:

- supported store adapters;
- versions and capabilities;
- runtime-ready versus discovery-only;
- compatibility checks;
- links to user `StoreProfile` records.

It is not a duplicate list of profiles.

### Activation trigger

Activate only when one of these is true:

1. a second real adapter exists;
2. users need adapter-level diagnostics independent of profiles;
3. adapter installation/version compatibility becomes a product concern.

Until then, known-store metadata remains code-owned, and the disabled route is honest.

## 4.11 Планировщик

**Status:** Future gate; disabled.

### Intended workspace

- schedule definitions;
- profile and report target;
- timezone and next run;
- enabled/disabled state;
- run-now;
- execution history and missed-run reason.

### Required future data

- `schedule_definitions`
- `schedule_executions` linked to generic workflow runs.

### Activation gate

No executor until the following are accepted on Windows:

- one browser owner and one mutation owner;
- crash/orphan recovery;
- machine sleep/restart semantics;
- duplicate/missed trigger policy;
- timezone/DST behavior;
- manual challenge behavior for unattended runs;
- update/install interaction;
- explicit user enablement.

A schedule definition without an executor may be designed later, but creating dormant tables in P0 provides no proven value.

## 4.12 Authoritative route-contract matrix

This matrix closes the complete route chain. Detailed sections 4.1–4.11 explain the workspace; this table is authoritative for ownership, events, gates, diagnostics and acceptance.

| Route | Intent and primary actions | Command/query | Aggregate and tables | Progress/events and terminal outcome | Permission/manual gate | Diagnostics and acceptance |
|---|---|---|---|---|---|---|
| **Исследование** | Research one site; start/retry/cancel; acknowledge manual action | `StartResearch`, `CancelRun`, `GetResearchRun`, `ListRunEvents` | `StoreProfile`, `ResearchRun`; profiles/versions, runs/events, catalog snapshots, journal | started → phase/progress → manual-action or snapshot-committed → `ready|blocked|manual_action_required|partial|failed|cancelled*` | Live retailer and manual challenge require explicit human approval/action | redacted worker trace and reason code; fixture equivalence, responsive GUI, one browser owner, no empty success |
| **Каталог** | Search tree, select nodes, collect products | `GetCatalogSnapshot`, `SearchCatalogNodes`, `ReplaceCatalogSelection`, `CollectProducts` | `CatalogSnapshot`, selection; snapshot JSON, P1 nodes/selections, product run/workspace | selection-changed, collection-started/progressed/terminal → `ready|partial|blocked|manual_action_required|failed|cancelled*` | No browser start with empty selection; collection inherits research/runtime gate | snapshot/projection lineage and selected URLs; merge selections without replacement, rebuild equivalence |
| **Товары** | Filter locally, inspect/select products, save preset/checkpoint | `GetProductWorkspace`, `FilterProductWorkspace`, `SetSelectedProducts`, `SaveFilterPreset`, `CreateProductWorkspaceCheckpoint` | `ProductWorkspace`; existing snapshots/presets, P1 identities/observations/items | workspace-changed, preset-saved, checkpoint-created; command outcome `ready|failed` | No destructive filter; ambiguous identity merge requires human resolution | source snapshot/run and missing-field warnings; GUI/CLI ID equivalence, reset restores all products |
| **Отчёт** | Choose scope/columns, preview, generate/open report | `GetReportScope`, `ListReportPresets`, `SaveReportPreset`, `GenerateReport`, `GetArtifact` | `ReportRun`; report presets, workspace checkpoint, P1 report runs/artifacts | report-started/progressed, artifact-created, terminal `ready|partial|failed|cancelled*` | Generation is explicit; restore/overwrite never implicit | preset/scope lineage, checksum, locked/missing-file reason; reproducible report and secret-free artifact |
| **Профиль** | Select workspace/profile, open/save version, rename/archive | `ListWorkspaces`, `ListProfiles`, `ListProfileVersions`, `OpenProfileVersion`, `SaveProfileVersion`, `RenameProfile`, `ArchiveProfile` | `ProjectWorkspace`, `StoreProfile`, `ProfileVersion`; central profile tables and linked snapshots | profile/version-created/opened/archived; `ready|blocked|failed` | Archive is explicit; no destructive delete in first release; opening starts no browser | cross-workspace/reference check and version provenance; complete restore without browser and no secret fields |
| **История цен** | Choose two captures, compare, inspect and export changes | `ListPriceSnapshots`, `ComparePriceSnapshots`, `GetProductPriceHistory`, `ExportPriceComparison` | `PriceSnapshot`/observations; existing price observations, P1 snapshot grouping, query/view changes | comparison-built, export-created; `ready|partial|blocked|failed` | Cross-profile comparison prohibited; export is explicit | currency/missing/availability reason codes and source lineage; idempotent observations and bounded-memory query |
| **Избранное** | Add/remove targets, refresh supported favorites | `ListFavorites`, `AddFavorite`, `RemoveFavorite`, `RefreshFavorites`, `CancelRun` | Favorites/refresh run; favorites and refresh run/result tables | favorite-changed, refresh-started/progressed/terminal `ready|partial|blocked|failed|cancelled*` | No default-store fallback; remove and live refresh are explicit | unsupported capability reason and owning profile; idempotent refresh, partial is not success |
| **Диагностика** | Run doctor/browser check, inspect run, export safe bundle | `RunDoctor`, `RunBrowserCheck`, `GetRun`, `ListRunEvents`, `VerifyArtifacts`, `CreateRedactedSupportBundle` | Diagnostic workflow/read model; runs/events, journal, migrations, artifacts | check-completed, integrity-issue, bundle-created; `ready|partial|failed` | Browser check makes no retailer request without separate approval; bundle export explicit | stable check/reason/remediation codes; deterministic read-only doctor and mandatory secret scan |
| **Прокси** | Enable/configure/test approved proxy route | `GetProxyConfigurationSummary`, `ReplaceProxyConfiguration`, `TestProxy`, `GetLatestProxyTest` | Proxy configuration/test; secret store outside product DB, optional redacted test history | proxy-test-started/completed; `ready|blocked|failed` | Credentials are never displayed/logged; disable does not silently delete; no paid/account action | masked endpoint, latency and safe egress facts; background execution, fail closed if secure store unavailable |
| **Магазины** | Future adapter/capability overview and compatibility check | Future `ListAdapters`, `GetAdapterCapabilities`, `RunAdapterCheck`; mutation commands only after activation | `AdapterRegistry` and existing store profiles; code registry first, future capability table only if dynamic | adapter-check/provision status; `ready|blocked|failed` | Remains disabled until second adapter or independent management value; adapter enable/install needs separate approval | capability/conformance report; no duplicate Profile UX and no “supported” claim without fixture suite |
| **Планировщик** | Future schedule definition, enable/disable, run-now and history | Future `ListSchedules`, `CreateSchedule`, `UpdateSchedule`, `EnableSchedule`, `DisableSchedule`, `RunScheduledNow` | `ScheduleDefinition`/execution; no P0 tables, future definitions/executions linked to runs | schedule-changed/due/execution-linked/missed; run terminal outcomes | Remains disabled until supervisor/ownership/recovery and explicit user enablement | DST/timezone, sleep, duplicate/missed trigger, orphan/crash-loop evidence; no unattended execution before Windows acceptance |

`cancelled*` is a recommended distinct outcome and remains a Product Owner decision until Gate 0 freezes compatibility mapping.

---

# 5. Application contracts

## 5.1 Contract rule

All presentation adapters call the same application interface. Contracts contain IDs, DTOs, enum values, paths/references and progress data — never Qt widgets, browser handles or live SQLite connections.

## 5.2 Proposed commands

| Command | Owner | Earliest phase |
|---|---|---|
| `StartResearch` | Research application service | P0 |
| `CancelRun` | Workflow control service | P0 |
| `ReplaceCatalogSelection` | Catalog selection service | P0/P1 |
| `CollectProducts` | Product collection workflow | P0 |
| `SetSelectedProducts` | Product workspace service | P0 |
| `SaveFilterPreset` | Preset service | P0/P1 |
| `CreateProductWorkspaceCheckpoint` | Product workspace service | P1 |
| `GenerateReport` | Report service | P0 |
| `SaveReportPreset` | Preset service | P0/P1 |
| `SaveProfileVersion` | Profile service | P0 |
| `OpenProfileVersion` | Profile application service | P0/P1 |
| `RefreshFavorites` | Favorite workflow | P0 |
| `TestProxy` | Proxy service | P1 |
| `RunDoctor` | Diagnostics service | P0/P1 |
| `CreateRedactedSupportBundle` | Diagnostics/artifact service | P1 |
| `CreateWorkspaceBackup` | Backup service | P2 |
| `RestoreWorkspaceBackup` | Backup service | P2, explicit gate |

## 5.3 Proposed queries

| Query | Owner/read model | Earliest phase |
|---|---|---|
| `GetLauncherSummary` | Launcher summary read model | P0 |
| `ListWorkspaces` | Workspace read model | P0/P1 |
| `ListProfiles` | Profile read model | P0 |
| `ListProfileVersions` | Profile-version read model | P0/P1 |
| `GetCatalogSnapshot` | Catalog snapshot read model | P0 |
| `SearchCatalogNodes` | Catalog search read model | P0 |
| `GetProductWorkspace` | Product-workspace read model | P0 |
| `FilterProductWorkspace` | Product-workspace read model | P0 |
| `GetReportScope` | Report-scope read model | P0 |
| `ListReportRuns` | Report-run read model | P1 |
| `ListPriceSnapshots` | Price-history read model | P1 |
| `ComparePriceSnapshots` | Price-comparison read model | P1 |
| `ListFavorites` | Favorites read model | P0 |
| `GetRun` | Workflow-run read model | P0 |
| `ListRunEvents` | Run-event read model | P0 |
| `GetDiagnosticsSummary` | Diagnostics read model | P0/P1 |
| `ListArtifacts` | Artifact-lineage read model | P0/P1 |

P0-A crosses only the queries needed by the deterministic research → catalog → product → report fixture. Route read models may internally compose repositories; the public application interface does not expose one getter per table.

## 5.4 Event envelope

**Proposed, not frozen:**

```json
{
  "contract_version": 1,
  "run_id": "...",
  "sequence": 1,
  "event_type": "run_started|phase_changed|progress|manual_action_required|artifact_created|terminal",
  "phase": "...",
  "progress": {"current": 0, "total": null},
  "message": "локализованный безопасный текст",
  "reason_code": null,
  "payload": {}
}
```

Rules:

- monotonic sequence per run;
- idempotency key for replayed events;
- schema version on every message;
- allowlist payload serialization;
- redaction before persistence;
- one terminal event per run;
- no progress after terminal.

## 5.5 Status compatibility

Do not replace the existing status field in one step. Separate lifecycle from terminal outcome.

### Proposed model

| Axis | Values |
|---|---|
| `run_state` | `queued`, `running`, `cancelling`, `terminal` |
| `terminal_outcome` | `ready`, `blocked`, `manual_action_required`, `partial`, `failed`, proposed `cancelled` |
| `reason_code` | stable machine-readable reason |
| `message` | localized user-facing text |
| `retryable` | boolean |

### Proposed compatibility projection pending Gate 1 inventory

| New state/outcome | Existing UI/manifest projection |
|---|---|
| not started | `idle` |
| queued/running/cancelling | `running` |
| ready | `succeeded` |
| partial | not frozen; legacy binary surfaces default to `failed` plus distinct `partial` reason/outcome until `D-14` approves another visibly non-successful representation; never ordinary `succeeded` |
| blocked/manual action/failed | `failed` with distinct reason/outcome |
| cancelled | current compatibility mapping to be approved; new UI must not call it an ordinary failure |

Gate 1 must inventory the literal status values and exit codes currently owned by GUI state, CLI and `RunManifest`, with file references. **Human gate:** `cancelled` and the exact `partial`/manual-action compatibility mapping must be frozen under `D-14` before P0 implementation.

## 5.6 CLI compatibility

Existing flags and `RunManifest` remain a compatibility surface until tests prove migration. Proposed future commands:

```text
parserriba doctor --json
parserriba browser-check --runtime <runtime> --json
parserriba run-profile <profile-id> --visible --json
parserriba resume-run <run-id> --json
parserriba cancel-run <run-id> --json
parserriba diagnostics export --run <run-id>
parserriba package-smoke --json
```

The final CLI contract must define:

- JSON/NDJSON schemas;
- exit-code mapping;
- stdout versus stderr;
- Ctrl+C/cancellation behavior;
- artifact references;
- blocked/manual/partial semantics;
- backward compatibility for current flags.

Gate 1 produces a named compatibility-baseline artifact containing current CLI flags, `RunManifest` fields, status literals and exit codes with file references. P0-A equivalence tests bind to that artifact; proposed commands and schemas do not replace it implicitly.

---

# 6. Data architecture

## 6.0 Source-verified current physical storage inventory

This is the source-defined physical baseline. “Source-verified” means that the declaring owner/path was inspected and is listed in section 1.1; it does not assert that every file exists in every checkout, validate user-file contents or grant permission to open user data.

| Physical store/path | Verified current owner/use | Classification and target treatment |
|---|---|---|
| `<repo-root>/data/profiles/store_profiles.db` | launcher profile/workspace repository (`launcher/desktop_project_workspace.py`, profile save/load controllers) | Current central StoreProfile DB; preserve in P0, migrate location only with Windows packaging/backup acceptance |
| `<repo-root>/data/products.db` | `ProductStorage`, onboarding/discovery repositories and local report tasks (`utils/site_onboarding.py`, `utils/local_task_registry.py`) | Current parallel operational/runtime DB containing `products`, `price_history`, onboarding and discovery tables; inventory/reconcile before cutover |
| `<task-output>/products.db` | store/product export path (`utils/store_export_runtime.py`) | Generated export SQLite artifact; never implicit operational source of truth |
| `<repo-root>/data/proxy_history.db` | Pyaterochka smoke/discovery script proxy-attempt ranking | Current contents unverified; do not read/migrate before a bounded secret-scan receipt; then keep isolated/redacted and never migrate credentials automatically |
| `<repo-root>/profiles/pyaterochka/...` | browser/runtime profile state (`utils/pyaterochka_runtime.py`) | Browser-owned files, not product DB; isolate per task and never expose/copy wholesale |
| `<repo-root>/data/runtime`, `data/reports` and task output directories | JSON manifests/snapshots, Excel and diagnostics | Artifacts/compatibility evidence; register lineage/checksum later, do not treat as canonical mutable state |

Current `ProductStorage` accepts an explicit path, so additional task/test SQLite files can exist. The migration inventory must discover actual DB files and schema versions without ingesting browser stores, secret files or generated exports into the canonical database.

## 6.1 Physical topology decision

**Recommendation:** one central SQLite database per user installation, containing multiple `ProjectWorkspace` records.

Why:

- the existing model already places `ProjectWorkspace` above `StoreProfile`;
- cross-workspace selectors and migrations remain simple;
- one local mutation owner can protect consistency;
- a separate database per route or per store would create reconciliation and backup complexity.

### Location

- **P0 proposed host (`D-08`):** add `schema_migrations`, `app_meta`, `workflow_runs`, `workflow_run_events` and `run_control_requests` only to `<repo-root>/data/profiles/store_profiles.db`. P0-A schema work remains blocked until the Product Owner freezes `D-08`.
- `<repo-root>/data/products.db` receives no new P0 tables. Existing compatibility reads/writes remain under their current owner until P1-B inventory/reconciliation; they are not promoted to canonical ownership by this plan.
- **P2:** migrate to an approved per-user Windows data directory only with packaging/backup tests.
- Do not silently relocate existing data.

### Connection policy

- `PRAGMA foreign_keys=ON` on every connection after foreign keys are introduced;
- bounded `busy_timeout`;
- WAL only after real backup/antivirus/packaging checks;
- one mutation owner for the central `store_profiles.db` P0 tables; another client is read-only or fails fast. The existing `data/products.db` compatibility owner remains separately inventoried until P1-B cutover;
- transaction commits define snapshot/run terminal visibility.

## 6.2 Data classes

| Class | Purpose | Examples |
|---|---|---|
| Aggregate metadata | Current user-owned objects | workspaces, profiles, product workspaces |
| Immutable snapshot | Exact reproducibility/restore | profile versions, catalog/product snapshots |
| Normalized projection | Efficient queries | catalog nodes, product identities/items |
| Append-only observation/event | History and evidence | run events, price observations |
| User definition | Reusable user configuration | filter/report presets, future schedules |
| Artifact registry | Local file lineage | Excel, JSON, diagnostic bundle, backup |
| Local settings | Device/UI preferences | theme, output path, layout |
| Secret store | Credentials/auth/browser state | outside product SQLite |

## 6.3 Existing central tables

| Existing table | Decision | Mutation owner | Routes |
|---|---|---|---|
| `project_workspaces` | **Keep/refactor:** aggregate root; add schema-backed constraints only through migration | Workspace service | All |
| `store_profiles` | **Keep/refactor:** one profile per site/domain inside a workspace; no secrets | Profile service | Research, Profile, Stores |
| `profile_versions` | **Keep:** immutable saved versions; add explicit lineage/uniqueness | Profile service | Profile, Research |
| `catalog_snapshots` | **Keep:** immutable envelope; add schema version/hash/run lineage later | Catalog snapshot service | Research, Catalog |
| `product_workspace_snapshots` | **Keep:** restore checkpoint, not long-term query model | Product workspace snapshot service | Products, Report |
| `filter_presets` | **Keep/refactor:** version definitions instead of destructive overwrite | Preset service | Products |
| `report_presets` | **Keep/refactor:** version definitions | Preset service | Report |
| `price_observations` | **Keep/refactor:** canonical temporal price facts after legacy reconciliation | Observation service | Price history, Products, Favorites |
| `workspace_journal_events` | **Keep:** user-facing journal projection, not raw event stream | Journal projector | Diagnostics/Profile |
| `workspace_favorites` | **Keep/refactor:** preserve workspace/profile ownership; link canonical identities later | Favorite service | Favorites |
| `favorite_refresh_runs` | **Keep:** compatibility/read model; may project generic runs later | Favorite service | Favorites |
| `favorite_refresh_results` | **Keep:** per-favorite results and reasons | Favorite service | Favorites |

## 6.4 Parallel/legacy data

| Existing parallel store | Decision |
|---|---|
| `products` | Freeze as legacy source during migration; deduplicate into canonical product identities only after inventory/reconciliation |
| `price_history` | Stop new writes only after canonical price observation cutover; backfill with count/timestamp checks |
| onboarding tables | Inventory callers; map durable profile facts to profile/version data and transient progress to run events |
| discovery tables | Preserve until catalog snapshot/projection equivalence is proven |
| proxy history | Treat current contents as unverified; require a secret-scan receipt before read/migration, then keep isolated/redacted and never migrate credentials automatically |
| generated export SQLite | Treat only as an artifact; never reopen implicitly as the operational DB |

No legacy table is deleted by this plan.

## 6.5 Minimal P0 additions

Avoid introducing the full future schema in P0. Add only what the first shared workflow needs.

All five P0 additions below target only `<repo-root>/data/profiles/store_profiles.db`, pending approval of `D-08`. `<repo-root>/data/products.db` gains no new P0 table.

| Proposed table | Key fields | Owner | Important indexes/constraints |
|---|---|---|---|
| `schema_migrations` | `version PK`, `name`, `checksum`, `applied_at`, `app_version` | migration runner | unique version/checksum |
| `app_meta` | `key PK`, `value_json`, `updated_at` | migration runner | `database_uid`, `minimum_reader_version` keys |
| `workflow_runs` | `run_id PK`, `workspace_id`, `profile_id`, `kind`, `run_state`, `terminal_outcome`, `reason_code`, timestamps, manifest JSON | Workflow service | workspace/time, state/time; one active conflicting run invariant |
| `workflow_run_events` | `event_id PK`, `run_id FK`, `sequence_no`, `event_type`, `phase`, progress, safe payload JSON, `created_at` | Run event store | unique `(run_id, sequence_no)` |
| `run_control_requests` | `request_id PK`, `run_id FK`, `kind`, `state`, `requested_at`, `acknowledged_at` | Workflow control service | run/state; idempotency key |

`artifacts` can remain embedded references for the first compatibility slice and move to a registry in P1.

## 6.6 P1 query/provenance tables

| Proposed table | Purpose | Key relationships |
|---|---|---|
| `catalog_nodes` | Rebuildable normalized catalog projection | catalog snapshot, parent node, source node key |
| `catalog_selections` | Explicit persisted node selection | workspace/profile/snapshot/node |
| `product_identities` | Stable product identity per store adapter | workspace/profile, adapter key, store product key |
| `product_observations` | Temporal normalized/raw product-card facts excluding duplicated price truth | product identity, source run/snapshot, observed time |
| `product_workspaces` | User-owned analysis workspace | workspace/profile/source snapshot |
| `product_workspace_items` | Membership/order/selection state | product workspace, product identity/observation |
| `report_runs` | Reproducible report lineage | workflow run, workspace checkpoint, preset version |
| `artifacts` | File registry | workspace, run/report, relative path, kind, size, checksum, state |
| `price_snapshots` | Groups price observations from one accepted capture | workspace/profile/run, observed time |

`price_changes` begins as a query/view. A materialized table requires measured performance evidence.

## 6.7 Future-gated tables

Do not create before activation:

- `schedule_definitions` / `schedule_executions`;
- adapter/plugin installation tables;
- supervisor leases/clients;
- mobile sync/conflict tables;
- cloud account/tenant tables.

## 6.8 Foreign keys and deletion policy

- Add foreign keys incrementally through shadow-table migrations and backups.
- `RESTRICT` deletion of objects referenced by accepted runs, snapshots and reports.
- `CASCADE` only true children such as run events.
- P0 performs no automatic deletion of user workspaces, profiles, snapshots, observations or artifacts.
- Prefer archive/tombstone state for profiles and workspaces until lifecycle is accepted.
- Missing artifact files remain registry state, not fatal corruption of the saved session.

## 6.9 Migration protocol

### P0-A migration safety

- Product Owner fact as of 2026-08-08: ParserRIba currently has no real users and no valuable production data. Existing local data may still contain useful development/WIP state and is not disposable by default.
- P0-A applies schema changes first to deterministic fixtures and verified copies. Existing local development DBs may be migrated only in an isolated worktree after fixture/copy checks; `D-18` stays dormant until real users or valuable production data exist.
- Before each fixture/copy migration, create an internal SQLite-safe backup copy with source/destination checksum, size and restore verification. This is a migration-runner guard, not the user-facing `CreateWorkspaceBackup`/`RestoreWorkspaceBackup` capability scheduled for P2.
- A proxy-history or browser-owned store is outside this migration path; no such file is opened without its own bounded secret-scan receipt and explicit scope.

Every migration follows:

```text
inventory
→ pre-migration backup
→ expand schema
→ validate
→ backfill
→ reconciliation report
→ repository cutover
→ compatibility window
→ explicit deprecation decision
```

Required checks:

- row counts and key-domain counts;
- min/max timestamps;
- orphan report;
- `PRAGMA foreign_key_check`;
- representative saved-session restore;
- price comparison equivalence;
- deterministic fixture hash;
- secret scan;
- old application blocked from opening an incompatible DB;
- rollback by restoring a verified backup, not destructive ad hoc DDL.

## 6.10 Route-to-data matrix

| Route/surface | Reads | Writes |
|---|---|---|
| Исследование | workspace, profile/version, capabilities | runs/events, profile version, catalog snapshot, journal |
| Каталог | catalog snapshot/nodes/selection | selection, product collection run |
| Товары | product workspace/items/observations, presets | selections, filter preset, checkpoint |
| Отчёт | workspace checkpoint, report preset | report run, artifact, journal |
| Профиль | workspaces, profiles, versions, snapshots | profile/version metadata, archive state |
| История цен | price snapshots/observations, products | normally query-only; export artifact when requested |
| Избранное | favorites, product/catalog identities, observations | favorites, refresh run/results |
| Диагностика | runs/events, migration issues, artifacts, journal | diagnostic run/event and support artifact |
| Прокси | local secret/config summary, redacted tests | secret/config outside DB; redacted test result only |
| Магазины | adapter capabilities and profiles | none until activated |
| Планировщик | future definitions/executions/runs | none until activated |
| Theme/layout settings | local launcher settings | local launcher settings, not StoreProfile |
| Backup/restore | central DB and artifact manifest | verified backup artifact or restored DB at explicit gate |

---

# 7. Delivery map

## Gate 0 — Product Owner freeze

**Status:** Approved on 2026-08-08. The Product Owner accepted `D-01` through `D-16` using the defaults recorded in section 10.

### Outcome

The target product flow, launcher IA, data topology and status/cancellation semantics are frozen for Gate 0.

### Approval record

- `D-01` through `D-16` are approved exactly as recorded in section 10.
- `D-17` (Codex route) and `D-19` (Git publication) remain separate pending gates and are not implied by Gate 0.
- `D-18` is a dormant future trigger, not a current blocker while the dated Product Owner fact in section 6.9 remains true.

### Done

This document and its SHA-bound Vault receipt name every frozen stable ID. No code, worktree, migration or publication was authorized by Gate 0.

## Gate 1 — Safe implementation baseline

**Status:** Approved 2026-08-08. The factual worktree/CLI/`RunManifest`/SQLite/test baseline is complete. `D-17` is approved and exact-path provisioned. Herdr now owns the accepted workspace/pane/process lifecycle and no-tool route; native tool/workspace-write execution is reproduced as blocked below Herdr. P0-A implementation remains unauthorized.

### Outcome

Create one isolated implementation worktree from an explicitly approved baseline.

### Work

- reconcile `specs/012` Draft/completed status;
- inventory current DB files/tables/callers;
- capture current targeted/full test baseline;
- freeze current CLI and RunManifest behavior;
- name the exact remote only if later commit/push is approved;
- do not clean/reset the dirty user WIP.

### Done

- clean isolated worktree;
- baseline commit/branch identified;
- no unrelated WIP copied;
- focused and full baseline evidence recorded.
- named CLI/RunManifest compatibility-baseline artifact records current flags, fields, status literals and exit codes with file references.

### Gate 1 execution receipt

- isolated worktree: `/home/hermesadmin/work/ParserRIba-worktrees/p0-application-workflow`;
- branch/HEAD: `codex/p0-application-workflow` / `7384328602249888d80f5a4631a4730d201ad4cc`;
- compatibility artifact: `/home/hermesadmin/out/parserriba-gate1-20260808/cli-runmanifest-contract-baseline.md`, SHA-256 `e25a3365b1c2455bd0ac7beb20fd34dd3bc5dc7f269c4e644eb1e8823639cf43`;
- Herdr reproduction summary: `/home/hermesadmin/out/parserriba-herdr-d17-20260808/herdr-d17-reproduction-summary.json`, SHA-256 `c8e254ebf7a4a75daef71b6dec2e480cabe3562473c7279f936ab0024b82c867`;
- static SQLite inventory: `/home/hermesadmin/out/parserriba-gate1-20260808/sqlite-static-inventory.json`, SHA-256 `76591e89cf75717319a1237ac7c3b0db50f2865207356dce136da9bbf6861b28`;
- source compile baseline passed; architecture/CLI/tests/launcher checks were captured and are environment-blocked by missing `loguru`, `playwright` and `PySide6`, not silently marked successful;
- `specs/012-launcher-information-architecture/spec.md` is absent from the approved commit and clean worktree; the protected dirty copy remains `Draft` and was not copied or promoted;
- `D-17` exact ParserRIba worktree allowlist passed static boundary tests. Herdr `0.7.5` owned workspace `w5` / pane `w5:p1` with the exact cwd and `HERDR_ENV=1`; its no-tool App Worker canary passed. The Herdr-owned workspace-write turn then reproduced three `name="exec_command"` plus `namespace="exec_command"` calls rejected as `unsupported call: exec_commandexec_command`; no marker or repository change resulted. Herdr correctly owned lifecycle and did not create the duplicated namespace;
- no implementation, package install, migration, commit, push, PR, runtime switch or live retailer run occurred.

## P0-A — Shared application contract

### Outcome

Current GUI and CLI call one `ApplicationWorkflow`/application-service path for a deterministic fixture.

### Work

- define command/query/event/result DTOs;
- freeze `FilterSpecV1` missing-field, ordering/tie-break, collation and error semantics;
- add lifecycle/outcome compatibility adapter;
- implement single-client cancellation contract;
- add migration scaffolding and minimal run/event tables only to the `D-08`-approved P0 host and only against fixtures/verified copies;
- keep current GUI and CLI behavior through adapters;
- one deterministic research/catalog/product/report fixture.

### Acceptance

- GUI and CLI produce equivalent manifest/result for the fixture;
- same terminal outcome and artifact references;
- no Qt/browser objects cross boundaries;
- cancellation before start, during progress and before commit is deterministic;
- schema migration is repeatable and rollback-tested using the internal checksum-bound fixture/copy backup; no existing local DB is migrated in place outside the isolated worktree, and `D-18` activates only when real users or valuable production data exist;
- focused tests plus full deterministic suite pass.

## P0-B — One accepted Pyaterochka vertical slice

### Outcome

One user can complete:

```text
Research
→ select catalog nodes
→ collect products
→ filter/select
→ generate report
→ save profile/version/price observations
→ reopen without browser
→ repeat and compare
```

### Work

- bind the real adapter only after deterministic P0-A;
- enforce one browser owner and isolated profile/trace directory;
- manual challenge result remains explicit;
- persist one accepted snapshot lineage;
- produce the named recurring report.

### Human/live gates

- explicit approval before live retailer run;
- user handles any manual challenge;
- challenges stop for human resolution; no CAPTCHA/WAF/login bypass or paid anti-captcha path;
- no second retailer/runtime expansion.

### Acceptance

- successful run, blocked/manual run and cancellation all produce honest terminal results;
- no orphan browser process/profile lock;
- reopening a saved version starts no browser;
- repeated snapshot comparison is correct;
- report is usable by the intended buyer/user.

## P1-A — Launcher coherence

### Outcome

Launcher routes, menu, inspector and responsive layout match this IA.

### Work

- one route registry for rail/view mapping;
- activate `Профиль` by regrouping existing controls;
- add application menu;
- move proxy test off GUI thread;
- strengthen Diagnostics and redaction tests;
- preserve product details ownership in inspector;
- responsive 960×760 and 1440×900 layouts.

### Acceptance

- no rail/tab mapping divergence;
- one primary workspace per route;
- no duplicated right panel;
- keyboard focus and accessible labels;
- responsive geometry checks at 960×760 and 1440×900 on the available desktop fixture; Windows DPI acceptance remains owned by P2;
- no business logic added to Qt presenters.

## P1-B — Canonical catalog/product/report data

### Outcome

Central DB supports efficient route queries without abandoning immutable snapshots.

### Work

- catalog projection and selection tables;
- product identities/observations/workspaces/items;
- report runs and artifact registry;
- immutable preset versions;
- legacy products/price inventory and reconciliation;
- no big-bang deletion.

### Acceptance

- snapshot → projection equivalence;
- ambiguous product identities are reported, not auto-merged;
- GUI/CLI local filtering equivalence;
- report reproducibility from immutable references;
- migration backup/rollback and foreign-key checks pass.

## P1-C — Price history route

### Outcome

User can compare two accepted captures and export an honest change report.

### Work

- price snapshot grouping;
- canonical product linkage;
- comparison query/view;
- route UI and inspector;
- price-history export through report/artifact services.

### Acceptance

- latest/previous and explicitly selected comparisons;
- currency/missing/availability cases distinguished;
- profile isolation;
- representative performance without full JSON loading.

## P2 — Windows production acceptance

### Outcome

A clean Windows machine can install, run, diagnose, update/repair or uninstall ParserRIba without losing user data.

### Work

- dependency lock/constraints and Python version freeze;
- resolve `scripts/build_windows.ps1` versus `ParserRIba.spec` entrypoint truth;
- package browser runtime/data intentionally;
- per-user data/settings/secret paths;
- installer strategy;
- optional signing/update only after explicit decisions;
- backup/restore and cleanup;
- accessibility/DPI/long-path/non-ASCII username tests.

### Acceptance matrix

- clean supported Windows environment;
- first launch and existing-data launch;
- 960×760, 1440×900 and selected DPI scales;
- keyboard navigation and UI Automation/NVDA checks;
- browser start/manual gate/cancel/crash cleanup;
- locked Excel/artifact cases;
- offline launcher startup where applicable;
- antivirus/Defender interaction with SQLite/WAL/worker;
- install, repair and uninstall preserve user data unless explicitly removed.

## P3 — Conditional expansion

Separate initiatives, not automatic continuation:

- unattended scheduler/supervisor;
- second store adapter;
- second production browser runtime;
- macOS packaging/signing/notarization/browser acceptance;
- iOS/Android companion and optional sync;
- cloud-assisted workspace.

Each requires a new Wayfinder/product decision and cannot reuse P0 approval implicitly.

---

# 8. Claude/Codex development through Herdr

## 8.1 One orchestration owner

Hermes remains the only orchestrator and final validator. Herdr manages bounded workspaces/panes. Claude and Codex are subordinate specialists.

## 8.2 Per-slice operating pattern

```text
Product Owner approves one slice
→ Hermes freezes Outcome / Scope / Constraints / Done / Context
→ isolated worktree and deterministic baseline
→ Herdr workspace
→ exact route/model canaries
→ one writer agent
→ focused checks
→ wide deterministic suite
→ second agent read-only review
→ Hermes verifies files, commands, receipts and Windows evidence
→ Product Owner gate
→ optional commit/push only with explicit authorization
```

Rules:

- Claude and Codex never write the same worktree concurrently.
- One slice has one writer.
- A reviewer does not silently fix findings.
- Browser ownership belongs to the approved runtime lane, not the planning/review agent.
- Agent outputs are evidence inputs, not accepted truth until Hermes verifies source and tests.
- No raw secrets, `.env`, cookies, browser profiles or user SQLite are sent to a model.

## 8.3 Suggested agent roles

| Stage | Primary | Secondary |
|---|---|---|
| UX/launcher IA | Claude read-only specialist | Codex adversarial reviewer |
| Domain/data model | Codex planner/reviewer | Claude repository evidence check |
| File-scoped implementation | One approved writer only | Other runtime read-only review |
| Difficult bug | Matt `diagnosing-bugs` flow + one implementer | independent root-cause review |
| Final code review | Matt `code-review` flow | Hermes deterministic verification |
| Windows acceptance | human/Windows harness owns result | agents analyze redacted outputs |

## 8.4 Current route blocker to resolve before Codex implementation

The accepted Codex App Worker currently allowlists read-only roots outside ParserRIba and permits workspace-write only in `/home/hermesadmin/work/claudiiii`. In this planning run Codex therefore received a bounded source packet rather than repository access.

Before Codex can implement ParserRIba through Herdr:

1. Product Owner explicitly approves a profile-local control-plane change.
2. Add only an isolated ParserRIba worktree root, never the dirty WIP tree.
3. Keep read-only and workspace-write allowlists separate.
4. Preserve Headroom/OpenCodex route, Telegram stripping and Hermes-tools disablement.
5. Run exact canary and a harmless read/write containment test.
6. Save and validate a redacted route receipt.

Until then:

- Claude may be used only through the accepted `claude-headroom` route and task-specific permissions.
- Codex is read-only packet reviewer for ParserRIba.
- No raw `codex exec`, no `danger-full-access`, no auth/provider bypass.

---

# 9. Verification strategy

## 9.1 Deterministic layers

1. schema/migration tests;
2. domain and application-service unit tests;
3. command/query/event contract tests;
4. GUI adapter tests without browser;
5. CLI JSON/NDJSON golden tests;
6. deterministic fixture integration;
7. browser/runtime control test;
8. one explicitly approved live retailer acceptance;
9. Windows package/install acceptance;
10. independent read-only review.

## 9.2 Required negative cases

- empty catalog selection;
- empty product result;
- partial catalog/product result;
- manual challenge required;
- browser startup failure;
- proxy failure and credential absence;
- cancellation at every lifecycle boundary;
- worker crash and stale lock;
- missing/locked artifact;
- corrupted or incompatible database;
- migration orphan/ambiguous product;
- secret-bearing error input;
- second GUI/CLI mutation attempt;
- non-ASCII paths and long Windows paths.

## 9.3 Completion evidence for every slice

- activated skills/workflow;
- baseline/worktree identity;
- exact files changed;
- focused tests and exit codes;
- full deterministic suite and exit code;
- migration/backup/rollback receipt when relevant;
- Windows evidence when required;
- independent review findings and disposition;
- unresolved risks;
- human gate still required.

---

# 10. Stable Product Owner decision register

On 2026-08-08 the Product Owner explicitly approved `D-01` through `D-16` using the recorded defaults and then separately approved `D-17` for the exact isolated ParserRIba worktree. `D-17` is provisioned but not implementation-ready because live native tool execution is blocked. `D-19` remains pending; `D-18` remains dormant under the dated no-current-users/data fact.

| ID | Decision | Frozen/default decision | Status |
|---|---|---|---|
| `D-01` | Launcher stack | Keep Python + PySide6 Qt Widgets through P2 acceptance | Approved 2026-08-08 |
| `D-02` | Profile route | Activate in P1 using existing profile/session behavior | Approved 2026-08-08 |
| `D-03` | Price-history route | Activate after canonical price lineage | Approved 2026-08-08 |
| `D-04` | Stores route | Adapter/capability registry; remain disabled until independently useful | Approved 2026-08-08 |
| `D-05` | Scheduler | Remain disabled until unattended ownership/recovery is accepted | Approved 2026-08-08 |
| `D-06` | App menu | `Файл / Вид / Инструменты / Справка` | Approved 2026-08-08 |
| `D-07` | Target database topology | One central SQLite per user installation with multiple workspaces | Approved 2026-08-08 |
| `D-08` | P0 physical database host | Put only P0 migration/run/event additions in `data/profiles/store_profiles.db`; add no P0 tables to `data/products.db` | Approved 2026-08-08 |
| `D-09` | P0 mutation model | One mutation owner for central P0 tables; second client read-only/fail-fast; preserve separately inventoried compatibility owner until cutover | Approved 2026-08-08 |
| `D-10` | Snapshot strategy | Immutable snapshots plus rebuildable normalized projections | Approved 2026-08-08 |
| `D-11` | Product deduplication | Never auto-merge ambiguous identities | Approved 2026-08-08 |
| `D-12` | Automatic retention | None for user data in P0 | Approved 2026-08-08 |
| `D-13` | Proxy history/secrets | Treat current contents as unverified; scan before read/migration; keep secrets outside product SQLite and migrate nothing automatically | Approved 2026-08-08 |
| `D-14` | Terminal outcomes and legacy mapping | Add distinct `cancelled`; only `ready` maps to ordinary success; freeze partial/manual/cancelled representation before P0 | Approved 2026-08-08 |
| `D-15` | Cancellation/application exit | Cooperative cancel/wait in P0; no forced worker termination; any future force policy requires a separate decision | Approved 2026-08-08 |
| `D-16` | First commercial proof | One payer/buyer, one recurring report, one Pyaterochka workflow | Approved 2026-08-08 |
| `D-17` | Codex implementation route | Hermes → Herdr lifecycle → approved Codex App Worker → OpenCodex/Headroom; exact isolated ParserRIba worktree only; dirty tree and broad parent remain denied | Approved 2026-08-08; Herdr lifecycle/no-tool route accepted; native tools blocked below Herdr; implementation readiness not accepted |
| `D-18` | First real-user/valuable-data migration | Dormant: no real users or valuable production data exist as of 2026-08-08; activate a separate approval only when that condition changes | Dormant future conditional trigger |
| `D-19` | Git publication | Separate explicit approval for commit, push or PR | Pending separate Git approval |

---

# 11. Immediate next gate

Gate 0 is closed. Gate 1 was separately approved and its factual baseline/worktree evidence is complete. The next action is still not P0-A implementation:

1. obtain separate approval for one bounded repair of the existing Codex App Server/tool-routing compatibility path now reproduced under Herdr; any package/runtime upgrade, provider/model/route change or service restart must be named and separately approved before execution;
2. repeat the same harmless exact-worktree marker canary through Herdr and require real file evidence plus clean post-cleanup Git status before declaring `D-17` implementation-ready;
3. only after that acceptance, produce a bounded **P0-A** implementation spec/ticket set, citing this master plan directly because `specs/012` is absent from the approved baseline, and request a separate implementation authorization.

`D-19` remains a later independent gate. `D-18` is dormant and becomes a separate gate only after real users or valuable production data appear; neither is granted by Gate 1 or `D-17`. Do not pre-create P1–P3 implementation branches or schema migrations.
