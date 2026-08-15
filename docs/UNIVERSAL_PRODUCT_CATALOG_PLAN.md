# ParserRIba Universal Product Catalog Plan

**Status:** active product plan
**Date:** 2026-08-10
**Current execution slice:** product Phase U5 offline adapter-onboarding boundary implemented for deterministic review; launcher-visible live profile exposure and every live collection remain separate human-approved gates.
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

- Bind each retained browser capability behind one opt-in registration that couples an exact declared `SourceProfile` to an exact injected `BrowserSourceAdapter`.
- Keep generic catalog/task imports browser-free, keep the default profile list source-neutral and move host markers, challenge logic and other source-specific settings into the registered profile/adapter boundary.
- Expose a live profile or run a live adapter only after a separate explicit user-approved live test plan.

**Offline boundary completed:** `BrowserSourceRegistration` lives in an opt-in module and validates one fixed HTTP(S) profile, explicit nodes and exact adapter identity. Generic catalog/task/registry imports use type-only references, so the browser module is absent from the default import path. Durable task input remains the source-neutral run/profile/node selection; raw browser profile/node objects and per-run locator overrides are rejected. Deterministic injected-runner coverage proves unrelated/default selections cannot dispatch the browser adapter, ready results enter the canonical `ProductWorkspace`, manual outcomes publish no products and unknown evidence fails before workspace publication. No browser was launched, no network was used and no optional dependency was installed.

**Acceptance status:** the offline registration/onboarding boundary is complete. Product Phase U5 remains open for the separately approved launcher-visible live profile, operational policy and live collection plan.

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

### Stage 0B — Cumulative-WIP stabilization (closed 2026-08-15)

- The accepted documentation/evidence boundary reconciled the multi-stage dirty worktree without rewriting Git history or treating residual WIP as one release unit.
- The 19 Stage 0A paths remained one exact frozen boundary. Twenty-two `.runtime` paths were represented only by aggregate count; names and contents remained excluded.
- The accepted slice changed only `docs/NEXT_STEPS.md`, this plan and `docs/DECISIONS.md`; it introduced no production, test, CI, dependency, runtime or live-source behavior.
- Stage 0B closure enabled the separately reviewed Stage 1 delivery. It did not authorize live browser/API `SourceProfile` exposure or live collection.

### Stage 1 — Universal desktop workspace and export (closed 2026-08-15)

- The launcher now owns a source-neutral `ProductWorkspace` lifecycle, explicit missing-aware filtering, exact product selection and explicit JSON export from canonical workspace state.
- Product observations, normalized products, field definitions and provenance remain separate; unavailable supplier/field values are not invented from legacy projections.
- Worker/subprocess results remain serializable and GUI-owned state is applied on the GUI thread.
- Deterministic acceptance and independent review closed the slice at delivered commit `291ba09b9af0aa42e66d1382a8e4a2e231cd60ae`; browser/API execution, user-database migration and legacy report migration were excluded.

### Stage 2 — Local catalogue picker and source-neutral tree (closed 2026-08-15)

- The local-file profile uses `QFileDialog` and a source-neutral `CatalogNode` tree populated from a strictly inspected local JSON document; editable internal category IDs are not exposed.
- Display labels and optional parent relationships come only from validated source records. Malformed nodes, duplicate/missing/self/cyclic parents, restricted material, invalid adapter identity and noncanonical `file:` locators fail closed.
- Inspection and collection use state-neutral JSON-safe workers. GUI callbacks alone apply and persist source locator, tree, selection and task state; source-invalidating failures clear stale projections while pre-dispatch input/scope/run errors preserve a valid tree.
- The delivered commit is `4551b54b1f76ce316e259dd1a6b78bdb780ed297`. The final deterministic contour passed 217 tests; immutable Standards review reported no findings and Spec review returned PASS. Full native Qt/PySide6 green status and live collection are not claimed.

### Stage 3 — Offline browser adapter onboarding (closed 2026-08-15)

- The retained browser adapter can be supplied only through an opt-in registration that binds one exact browser profile, fixed safe locator, explicit nodes and exact adapter identity.
- The default declared profile list and generic catalog/task/registry import path remain browser-free. Selection of an unrelated source cannot dispatch the injected browser runner.
- Deterministic ready, manual-action and invalid-evidence paths use only an injected fake runner and the canonical `ProductWorkspace`; live browser/network behavior and optional dependency installation were excluded.

### Next gated decision — U5 live adapter exposure

- Define the explicit launcher-visible live profile and its per-source operational policy without introducing generic retailer, host, category, output-path or anti-bot defaults.
- Freeze a user-approved same-session live test plan before exposing or invoking any live runner.
- Browser launch, optional dependency installation, credentials/provider changes and every live collection remain separate approvals.

## Explicit exclusions

- No paid scraping, CAPTCHA-solving, cloud LLM, cloud browser or mandatory backend service.
- No automatic CAPTCHA bypass or protected-request replay.
- No deletion of archive history, knowledge-base profiles, user data, browser profiles, cookies, credentials or operational databases in this plan slice.
- No claim of universal live-source support before U1–U5 acceptance gates pass.
- No release, package install, automatic live-profile exposure or live retailer execution is implied by this plan. Commit, push and PR actions remain separately approved per delivery slice.

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
