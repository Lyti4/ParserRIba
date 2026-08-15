# ParserRIba Universal Product Catalog Plan

**Status:** active product plan
**Date:** 2026-08-10
**Current execution slice:** Stage 0B cumulative-WIP stabilization, following accepted Stage 0A security/explicit-boundary closure on 2026-08-14.
**Supersedes as active planning sources:** the predecessor roadmap, launcher architecture and Launcher V2 spec, now retained under `archive/project_history/universalization_2026-08-10/`.

## Outcome

ParserRIba becomes a local-first program for working with products from **arbitrary sources**. A user can create or select a source, inspect/import its catalogue, select explicit catalogue nodes or an explicit input set, collect product observations, filter them, inspect provenance, and export a chosen set.

The product does not start from a specific retailer, URL, product category, or product class. Pyaterochka may remain as an adapter regression case and deterministic fixture, but it is not the launcher default, universal runtime, or roadmap gate.

## Current evidence

The 2026-08-10 source and documentation audit found:

- the generic `application/` workflow already has deterministic no-network lifecycle, cancellation, filtering and event contracts;
- discovery/catalog/profile concepts already exist, but the visible launcher and export path default to `pyaterochka`, `5ka.ru`, `fish_catalog` and `wine_catalog`;
- the current active documentation has duplicate and conflicting product directions;
- archive documents are historical evidence; knowledge-base profiles are active source-specific data and are not safe deletion candidates.

This plan changes the product direction and documentation only. It does not claim that the existing runtime is already universal.

## Product model

Use the glossary in `CONTEXT.md`.

```text
SourceProfile
  -> explicit CatalogNodes or explicit input set
  -> SourceAdapter collection
  -> ProductObservations with Provenance
  -> NormalizedProducts + extensible FieldDefinitions
  -> ProductWorkspace
  -> filters / explicit selection
  -> local Export
```

### Universal collection seam

The future public seam is one source-neutral collection operation:

```text
collect(CollectionRequest) -> CollectionResult
```

`CollectionRequest` contains one SourceProfile, explicit selected CatalogNodes or an explicitly named imported input set, and permitted runtime settings. `CollectionResult` returns observations, normalized products when possible, field definitions, provenance, artifacts, diagnostics and terminal outcome.

The launcher, report core and storage do not branch by fish/wine/retailer. Only the selected SourceAdapter handles source-specific behavior. This is a deep module seam: callers learn one collection interface while adapter complexity remains local.

### Source types and safety

| Source type | Initial role | Network default |
|---|---|---|
| deterministic fixture | acceptance tests, launcher demos | disabled |
| local file | safe user import path | disabled |
| browser adapter | optional site discovery/collection | disabled until explicitly invoked |
| API adapter | optional confirmed permitted API path | disabled until explicitly invoked |

No adapter may automatically solve CAPTCHA, replay protected requests, expose secrets, or convert diagnostics into product facts. The existing manual challenge handoff remains an optional, separately gated browser capability.

## User workflow

1. Create or choose a SourceProfile.
2. Provide an explicit source locator or select a fixture/local-file source.
3. Run discovery/import for that source when applicable.
4. Review the resulting catalogue or input summary.
5. Select explicit CatalogNodes or an explicit import set; the UI starts with nothing selected.
6. Collect products through the selected SourceAdapter.
7. Inspect products, fields, source provenance and collection limitations.
8. Filter the ProductWorkspace using discovered fields; missing values remain visible unless strict filtering is requested.
9. Select exact products or explicitly export the current filtered workspace.
10. Write local JSON/Excel artifacts and preserve only safe provenance/diagnostics.

## Delivery phases

### Phase U0 — Documentation and terminology (completed 2026-08-10)

- Establish `CONTEXT.md`, this plan, source-adapter rules and a compact operations guide.
- Remove Pyaterochka-first claims from current guidance.
- Archive superseded current plans after updating every active pointer.
- Retain historical archive and knowledge-base documents.

**Completed:** the active plan, glossary, source-adapter rules and operations guide are in place; superseded active documents are retained in the dated archive. Pointer, diff and deterministic-regression verification remains part of this documentation slice's completion evidence.

### Phase U1 — Source-neutral application contracts (completed 2026-08-10)

- Add `SourceProfile`, `CatalogNode`, `CollectionRequest`, `ProductObservation`, `NormalizedProduct`, `FieldDefinition` and `Provenance` contract shapes at the existing `application/` seam.
- Preserve P0-A lifecycle, cancellation, safe event payloads, deterministic filtering and compatibility projection.
- Ensure source identity and selected-node provenance are explicit and source-neutral.
- Do not migrate operational databases or start a browser/live source.

**Acceptance:** deterministic fixture tests prove no implicit source/category/product-type default and verify provenance for every product.

**Completed:** the existing `application/` seam now provides versioned source-neutral request/result, observation, normalized-product, field-definition and provenance shapes. Deterministic contract coverage enforces explicit source/node selection, no category/product-type default, safe non-secret mappings and locators, timezone-bearing observation timestamps, and exact observation-to-product provenance. P0-A lifecycle, cancellation, filtering and compatibility projection were retained; no browser, live-source or operational-database behavior was added.

### Phase U2 — Generic fixture and local-file adapters (completed 2026-08-10)

- Introduce a source-adapter registry with two real adapters: generic deterministic fixture and local-file import.
- Retain `application/pyaterochka_fixture.py` as one adapter test case until a generic fixture registry has comparable coverage.

**Acceptance:** two distinct fixture/input adapters use the same `collect(CollectionRequest)` seam; generic tests use synthetic/example sources rather than retailer URLs.

**Completed:** `application/source_adapters.py` provides explicit registry lookup, a generic synthetic fixture and a strict local JSON v1 importer. The file adapter permits only canonical hostless absolute `file:///` selection, validates its complete input before selection filtering, preserves source-neutral provenance and rejects ambient defaults, proxy/session-style configuration and unsafe product mappings. U2 deterministic adapter coverage is synthetic/example-only; no launcher, browser, API, database or legacy retailer behavior changed.

### Phase U3 — Launcher source workflow (completed 2026-08-10)

- Replace generic launcher defaults for `shop`, `intent`, hardcoded `5ka.ru`, fish and wine with blank explicit source/profile and catalogue-node inputs.
- Replace the active product-facing fixture panel with a generic source-adapter collection panel; retain legacy compatibility controls only as blank, explicit selections.
- Pass a declared profile/adapter identifier into the existing local launcher task boundary; never select an adapter from a product intent or category.

**Acceptance:** the launcher demonstrates two non-retailer fixture/file sources with no preselected catalogue nodes and no live network dependency.

**Completed:** `application/source_profile_catalog.py` declares exactly the synthetic fixture and explicit local JSON file profiles shared by the panel and task. The active collection tab starts with blank SourceProfile, locator and node values; blank profile/node selection fails before subprocess dispatch. The file profile accepts only a canonical hostless absolute `file:///.../*.json` locator at the declared-profile boundary; the public launcher task wrapper validates the complete explicit request before spawning. `DesktopLauncherController` forwards only the explicit profile, validated locator and node IDs through `source_adapter_collection` → `SourceAdapterRegistry.collect`. Launcher state, compatibility URL/store controls and preview rendering no longer infer a retailer, product intent or `5ka.ru` URL; blank/unknown legacy export or onboarding intent fails before task/browser dispatch, preview catalog JSON is script-safe, and artifact opening accepts only absolute local paths. The local-file path is covered through the real controller/subprocess/registry adapter chain; no browser/API call, user database, credentials, challenge logic or optional dependency was added.

### Phase U4 — Universal storage, filters and exports (completed 2026-08-10)

- Store observations, normalization state, declared field definitions and provenance separately from user-facing projections.
- Keep filtering non-destructive and export based on explicit product, an explicit non-empty filtered selection, or explicit whole-workspace selection.
- Leave fish/wine reports, launcher panels, user databases and browser/API capabilities outside this application/local-task slice.

**Completed:** `application/workspace.py` introduces the source-neutral `ProductWorkspace` seam. It aggregates one or more `CollectionResult` values without merging source-specific fields or provenance, rejects conflicting declared `FieldDefinition`s, and persists only canonical observations/products/declared definitions in strict `parserriba-product-workspace-v1` JSON. Declared facets and dynamically discovered scalar leaves from nested `attributes.*`/`source_fields.*` data coexist; filtering returns an immutable selection with missing values visible unless `strict=True`. JSON export requires selected product IDs, an explicit non-empty filtered selection, or an explicit whole-workspace flag, preserves raw nested attribute/source values, and includes flat `provenance.*` columns only when requested. The existing `source_adapter_collection` task writes the canonical artifact under its resolved `root_dir/workspaces/<filename-safe-collection_run_id>.json` and publishes it as `workspace_json`; explicit SourceProfile/node dispatch is otherwise unchanged.

**Acceptance:** products with different optional fields coexist; unknown scalar fields appear as discovered facets; cross-source export carries source/provenance columns when requested; no implicit export selection, relative output path, browser/API call or user-database migration is introduced.

### Phase U5 — Optional source capabilities

- Convert current Pyaterochka browser/API code into an opt-in SourceAdapter without global host, output-path or anti-bot defaults.
- Move host markers, challenge logic and source-specific browser profiles into per-source configuration.
- Add adapters only after fixture/file contract coverage and an explicit user-approved live test plan.

**Acceptance:** a live adapter is unreachable unless explicitly selected; no generic module imports a retailer script, URL, category or selector.

### Phase U6 — Legacy and release hardening

- Replace stale CLI/Docker/CI retailer demos with deterministic source-neutral acceptance fixtures.
- Archive legacy parsers only after import/reference checks and adapter replacements.
- Package the desktop product only after the generic fixture/file workflow is end-to-end usable.

## Cross-cutting stabilization checkpoints

The Stage checkpoints below reconcile cumulative implementation evidence across the delivery phases. They do not renumber or replace U0–U6.

Historical U5–U13 work-unit/receipt labels retained in `docs/NEXT_STEPS.md` belong to a separate implementation-continuation namespace. They do not close or renumber the product delivery phases in this plan; in particular, product Phase U5 and Phase U6 remain open until their own acceptance gates are satisfied.

### Stage 0A — Security and explicit-boundary closure (closed 2026-08-14)

- Final-current v4 froze 19 paths and closed fail-closed URL/artifact safety, explicit live/task identities, pre-side-effect validation, source-fidelity and safe manifest/logging boundaries.
- The frozen manifest SHA-256 is `38a405d15e7fa7f0cd982bde569259f3ee689ec58223e1a009aed1eadfcafe8a`; final identity verification found `0/19` mismatches.
- Targeted `90/90`, dependency-light `88/88 + 12/12 + 23/23`, expanded deterministic `179/179`, static checks and desktop smoke passed. Independent Standards and Spec reviews returned `PASS — No findings`.
- This acceptance does not claim a clean full worktree, full pytest success, live-source exposure, commit or delivery.

### Stage 0B — Cumulative-WIP stabilization (active)

- Initial inventory is 158 WIP paths: 51 modified, 14 renamed and 93 untracked. It contains multiple historical/current slices and is not one release unit.
- The 19 Stage 0A paths are present as one exact frozen boundary. Twenty-two `.runtime` paths are represented only by aggregate count; names and contents remain excluded.
- Stage 0B is documentation/evidence-only: `docs/NEXT_STEPS.md`, this plan and `docs/DECISIONS.md`. It does not change production code, tests, CI, dependencies, runtime state or Git history.
- Completion requires consistent active lifecycle pointers, deterministic inventory/pointer/diff checks and independent hash-bound review of the three-file slice.
- Stage 1 universal desktop export follows only after Stage 0B acceptance. Live browser/API `SourceProfile` exposure and every live collection remain separately frozen and approved.

## Explicit exclusions

- No paid scraping, CAPTCHA-solving, cloud LLM, cloud browser or mandatory backend service.
- No automatic CAPTCHA bypass or protected-request replay.
- No deletion of archive history, knowledge-base profiles, user data, browser profiles, cookies, credentials or operational databases in this plan slice.
- No claim of universal live-source support before U1–U5 acceptance gates pass.
- No commit, push, release, package install or live retailer execution.

## Documentation consolidation in U0

### Keep as active references

- `README.md`
- `AGENTS.md`
- `CONTEXT.md`
- `docs/UNIVERSAL_PRODUCT_CATALOG_PLAN.md`
- `docs/NEXT_STEPS.md`
- `docs/TARGET_ARCHITECTURE.md`
- `docs/DATA_FLOW_THREADING_PLAN.md`
- `docs/PROJECT_STRUCTURE.md`
- `docs/SOURCE_ADAPTERS.md`
- `docs/OPERATIONS.md`
- `docs/DECISIONS.md`
- `docs/LEGACY_MIGRATION_BACKLOG.md`
- `docs/PROJECT_FILE_FLOW_MAP.md` as generated evidence, not planning authority

### Archived in U0

- `archive/project_history/universalization_2026-08-10/active_docs/ROADMAP_V1.md`
- `archive/project_history/universalization_2026-08-10/active_docs/PROJECT_STATE.md`
- `archive/project_history/universalization_2026-08-10/active_docs/LAUNCHER_ARCHITECTURE.md`
- `archive/project_history/universalization_2026-08-10/active_docs/PLATFORM_FOUNDATION.md`
- `archive/project_history/universalization_2026-08-10/active_docs/DATA_INTERCEPTION_PLAN.md`
- `archive/project_history/universalization_2026-08-10/active_docs/TOOLS_POLICY.md`
- `archive/project_history/universalization_2026-08-10/active_docs/AUTOMATIONS.md`
- `archive/project_history/universalization_2026-08-10/active_docs/ARCHITECTURE_STEWARD.md`
- `archive/project_history/universalization_2026-08-10/active_docs/INSTALLATION.md`
- `archive/project_history/universalization_2026-08-10/active_docs/INSTALLER_ROADMAP.md`
- `archive/project_history/universalization_2026-08-10/active_docs/RELEASE_CHECKLIST.md`
- `archive/project_history/universalization_2026-08-10/active_docs/WINDOWS_QUICKSTART.md`
- `archive/project_history/universalization_2026-08-10/superpowers/specs/2026-05-23-launcher-v2-discovery-workflow-design.md`
- `archive/project_history/universalization_2026-08-10/superpowers/plans/2026-05-28-launcher-data-flow-isolation.md`
- `archive/project_history/universalization_2026-08-10/implementation_tickets/P0_A_SHARED_APPLICATION_CONTRACT_SPEC_20260809.md`

### Generated cache cleanup

- Pytest's generated, ignored README metadata had no project dependency and was removed as housekeeping. It regenerates on the next pytest run.

## Validation for this documentation slice

1. Every active pointer names only an existing active document.
2. No current planning document declares Pyaterochka, fish, wine or `5ka.ru` as a product default.
3. Archive and knowledge-base folders remain intact.
4. `git diff --check` passes.
5. A repository-local Markdown pointer scan reports no broken active targets.
