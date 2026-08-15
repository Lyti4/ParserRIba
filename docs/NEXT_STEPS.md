# ParserRIba Next Steps

**Active plan:** `docs/UNIVERSAL_PRODUCT_CATALOG_PLAN.md`
**Vocabulary:** `CONTEXT.md`

## Completed — U0 documentation consolidation

1. Replace active Pyaterochka-first planning pointers with the universal source/product plan.
2. Keep `README.md`, `AGENTS.md`, `CONTEXT.md`, `docs/UNIVERSAL_PRODUCT_CATALOG_PLAN.md`, `docs/TARGET_ARCHITECTURE.md`, `docs/DATA_FLOW_THREADING_PLAN.md`, `docs/PROJECT_STRUCTURE.md`, `docs/SOURCE_ADAPTERS.md`, `docs/OPERATIONS.md`, `docs/DECISIONS.md` and `docs/LEGACY_MIGRATION_BACKLOG.md` as the active documentation set.
3. Move superseded plans, status snapshots and product-specific operational notes to `archive/project_history/` after incoming pointers are updated.
4. Keep `archive/` and `knowledge_base/` intact; remove only verified generated cache metadata.

**Completion evidence:** active docs no longer establish a retailer, `5ka.ru`, fish or wine as a product default; pointers resolve; obsolete active plans are archived; generated cache README metadata is removed.

## Completed — U1 source-neutral contracts

### Outcome

Add the smallest SourceProfile/SourceAdapter contract to the existing `application/` seam without modifying browser or live-source behavior.

### Scope

- Source-neutral request/result and provenance types.
- Explicit `CollectionRequest` selection and terminal outcomes.
- Compatibility projection into existing launcher/run-manifest models where necessary.
- Deterministic generic fixture tests.

### Exclusions

- No browser/API call, no live retailer run, no optional-dependency installation.
- No migration of user databases or browser data.
- No fish/wine classifier/report rewrite in this slice.
- No removal of legacy adapters.

### Completion evidence

- Versioned source-neutral request/result, product and provenance contracts exist at `application/`.
- Contract tests prove explicit source/node selection, no source/category/product-type default and exact product lineage.
- Secrets, browser/session data and raw proxy values are rejected from generic contract data.
- Existing P0-A deterministic tests remain green; `compileall` and `git diff --check` pass.

## Completed — U2 generic fixture and local-file adapters

### Outcome

Two deterministic source-neutral adapters now use the completed `collect(CollectionRequest) -> CollectionResult` seam: a generic synthetic fixture and a strict user-selected local JSON v1 importer.

### Completion evidence

- `application/source_adapters.py` provides explicit registry lookup with no fallback/default source selection.
- `local-json-file-v1` accepts only canonical hostless absolute `file:///.../*.json` input, validates its complete JSON v1 document before selection filtering and preserves per-product provenance.
- Product configuration is allowlisted; extensible `source_fields` and `attributes` remain subject to the source-neutral sensitive-data contract.
- Deterministic tests cover synthetic and file collection, explicit nodes, undeclared nodes, unsafe root/product fields, unsafe unselected records and noncanonical/nonlocal locators.
- WIP Spec review passed. Standards review found the initial ambient-relative-file path gap; it was fixed with a RED→GREEN regression before completion.
- No launcher defaults, browser/API behavior, user databases, cookies, credentials or challenge code changed.

## Completed — U3 launcher SourceProfile workflow

### Outcome

The active launcher collection path is now default-free and dispatches only explicit source/profile/node selections through the existing local task boundary.

### Completion evidence

- `application/source_profile_catalog.py` declares two launcher-visible non-retailer sources: deterministic synthetic fixture and strict local JSON file.
- The active source-adapter panel lists both but starts with blank SourceProfile, file locator and catalog-node inputs; the compatibility URL/store controls and launcher state are blank as well.
- Controller validation rejects a blank source or node selection before subprocess launch. The selected adapter task receives only `collection_run_id`, `source_profile_id`, explicit node IDs and the required canonical hostless absolute `file:///.../*.json` locator for the local-file profile; its public wrapper validates this complete request before spawning.
- Source collection uses `source_adapter_collection` → local registry → `SourceAdapterRegistry.collect`; no product intent/category selects the adapter.
- Deterministic tests cover fixture dispatch, registry dispatch, blank-selection rejection, pure-UI blank state and a real local-file controller/subprocess/registry round trip. They also cover remote/relative/hosted locator rejection, script-safe preview JSON, no blank-intent fallback, and local-only artifact opening. Browser preview has no ambient retailer URL or product-source default.
- Browser/API execution, user databases, credentials, cookies, challenge code and optional-dependency installation remain excluded.

## Completed — U4 universal storage, filters and exports

### Outcome

`application.workspace.ProductWorkspace` stores canonical observations, normalized products, declared field definitions and provenance separately from filter/export projections. It supports cross-source declared and nested-leaf dynamic facets, immutable missing-aware filtering and explicit local JSON export.

### Completion evidence

- `parserriba-product-workspace-v1` stores canonical records only at an explicit absolute local JSON path and reloads through the source-neutral contracts.
- Products with different optional `attributes`/`source_fields` coexist; declared fields plus scalar leaves from nested values become `attributes.*`/`source_fields.*` facets without a retailer schema. Missing values remain visible unless `WorkspaceFilter(strict=True)` is explicitly selected; conflicting declared definitions fail closed.
- Export requires selected product IDs, an explicit non-empty filtered selection, or an explicit whole-workspace selection. Raw nested attributes/source fields are retained in rows; provenance columns are emitted only when requested; implicit selection and relative paths fail closed.
- The established U3 collection task writes `artifact_paths["workspace_json"]` only under its resolved task-root `workspaces/` directory using a filename-safe run ID; explicit profile/node validation and adapter dispatch remain unchanged.
- No launcher workspace-panel rewrite, browser/API source, user database migration, legacy report rewrite or optional dependency installation occurred.

## Accepted bounded work-unit receipts — separate from product phases

The U5–U13 identifiers below are preserved historical work-unit/receipt labels from the implementation continuation chain. They are not the U5/U6 product delivery phases defined by `docs/UNIVERSAL_PRODUCT_CATALOG_PLAN.md`, and their acceptance does not mark either product phase complete. The active product plan is authoritative for phase status.

## Accepted work unit U5 — recorded legacy fixture adapter

### Outcome

The retained DOM-derived and captured API-shaped legacy evidence forms are available as strict deterministic records behind one opt-in fixture-only `SourceAdapter`. No live source, launcher profile or production task exposure was added.

### Completion evidence

- `RecordedLegacyFixtureSourceAdapter` accepts only an explicit fixture profile, fixed recorded-fixture locator and explicit selected nodes through a test-constructed registry.
- Versioned DOM/API records preserve source/node/run provenance, validate all records before selection and fail closed on unsafe/unknown content, duplicate cross-shape identities and evidence outside the fixture namespace.
- Blocked/manual fixtures return no invented products. Optional browser dependencies are not imported.
- U5 tests pass 7/7; autonomous deterministic suites pass P0-A 50/50, P0-B 10/10 and P0-C 11/11; Ruff, compileall and `git diff --check` pass.
- The root legacy test harness is not dependency-clean in this environment: collection remains blocked by absent optional `loguru`, `camoufox` and `playwright`. Those packages were not installed or pulled into U5.

## Accepted work unit U6 — source-neutral CI baseline

- `scripts/run_dependency_light_ci.py` validates the legacy import-classification manifest and runs P0-A/P0-B/P0-C in deterministic order using `unittest`.
- `.github/workflows/ci.yml` has a separate `dependency-light-baseline` job pinned to CPython 3.11.15. It installs only the hash-locked source-neutral Pydantic stack from `requirements-dependency-light.txt`; it does not install Camoufox, Playwright, Loguru or OS browser libraries.
- `scripts/classify_legacy_test_dependencies.py` statically traces runtime-reachable imports without importing or executing legacy tests. The optional package invariant is code-owned rather than manifest-owned. At U6 closure, `tests/legacy_optional_dependency_tests.json` classified 20 root test modules and the dependency-light baseline passed 79/79.
- The manifest is evidence, not a skip/deletion list. Legacy tests and the existing browser-enabled CI job remain unchanged.

## Accepted work unit U7 — architecture-check boundary

- `scripts/architecture_check.py` no longer imports optional Loguru merely to present its deterministic Markdown report. A deliberate `stderr` CLI output wrapper preserves the report and exit-decision seam without adding any browser or live capability.
- The U7 regression imports and exercises the architecture-check renderer/output with Camoufox, Loguru and Playwright explicitly blocked.
- Existing architecture-check behavior passes 5/5 targeted tests. The current dependency-light baseline passes 80/80, while the static manifest now classifies 19 root legacy test modules with zero drift; only `tests/test_architecture_check.py` left the optional-dependency set.

## Accepted work unit U8 — KB loader boundary

- `utils/kb_loader.py` no longer imports optional Loguru for its source-neutral Markdown/Pydantic parsing API or standalone demonstration. The demo uses standard-library logging while preserving its INFO/error messages; no parsing, browser or live behavior changed.
- The U8 regression imports `KBLoader` and parses a local Markdown fixture with Camoufox, Loguru and Playwright explicitly blocked. Existing KB behavior passes 29/29 targeted tests.
- The current dependency-light baseline passes 81/81. The static manifest classifies 18 root legacy test modules with zero drift, and expected-blocked root discovery improves to 112 total / 94 runnable / 18 optional import errors; only `tests/test_kb_loader.py` left the optional-dependency set.

## Accepted work unit U9 — product-sampling boundary

- `utils/product_sampling.py` no longer imports optional Loguru for local async selector sampling. Standard-library logging preserves diagnostic levels/messages while selector order, exception fallback and return values remain unchanged.
- The U9 regression imports and exercises the public async text-selection seam with Camoufox, Loguru and Playwright explicitly blocked. Existing product-sampling behavior passes 4/4 targeted tests.
- The current dependency-light baseline passes 82/82. The static manifest classifies 17 root legacy test modules with zero drift, and expected-blocked root discovery improves to 112 total / 95 runnable / 17 optional import errors; only `tests/test_product_sampling.py` left the optional-dependency set.

## Accepted work unit U10 — human-behavior boundary

- `utils/human_behavior.py` no longer imports optional Loguru for source-neutral behavior profiles and duck-typed async page/mouse routines. Standard-library logging preserves diagnostic levels/messages while cooldown selection, randomization, browser calls and return values remain unchanged.
- The U10 regression imports and exercises the public deterministic cooldown seam with Camoufox, Loguru and Playwright explicitly blocked. Existing human-behavior behavior passes 4/4 targeted tests.
- The current dependency-light baseline passes 83/83. The static manifest classifies 16 root legacy test modules with zero drift, and expected-blocked root discovery improves to 112 total / 96 runnable / 16 optional import errors; only `tests/test_human_behavior.py` left the optional-dependency set.

## Accepted work unit U11 — additive structured-product browser evidence

- **Lifecycle status:** accepted on 2026-08-14 after explicit human approval and deterministic closure of all three fail-closed gates: encoded sensitive query-key forms; report-layer URL scheme/userinfo validation; and non-finite numeric values (`NaN`/`Infinity`) across structured evidence and report serialization.
- U11 follows the human correction that the working browser path is a product capability to strengthen, not remove. No browser, fingerprint, proxy, GeoIP, persistent-profile, navigation, selector, human-behavior or same-session manual-challenge capability was removed or replaced.
- `utils/structured_product_evidence.py` uses the already-declared BeautifulSoup browser-stack dependency to read only already-rendered HTML and extract bounded JSON-LD `Product` evidence. It retains only allowlisted name/SKU/brand/offer/URL fields, sanitizes known diagnostic URL assignments and deeply encoded sensitive values, rejects sensitive assignments and invalid Unicode in every non-URL allowlisted field, drops URL fragments, ignores malformed, oversized, over-deep or unsafe inputs, caps rendered HTML, script scan, traversal and evidence, and never promotes evidence into canonical products. Encoded sensitive query keys are bounded-decoded and sanitized; unresolved nested key encoding fails closed.
- `scripts/smoke_pyaterochka_support.py` adds the evidence under a separate `structured_product_evidence` field. `products_sample` remains the existing DOM-card path. Blocked/challenge and HTTP-403 results fail closed with empty structured evidence.
- `utils/smoke_report.py` renders a separate `Structured Product Evidence` section only for non-blocked/non-403 results; a blocked report hides structured evidence even if a caller supplies it incorrectly. Structured report URLs now allow only absolute HTTP(S) URLs with a hostname and no userinfo; unsafe fields are dropped. Non-finite numbers are dropped before report serialization. Bounded entry counts, malformed/secret/invalid-Unicode values and inert single-line Markdown escaping remain covered.
- Current deterministic evidence: 24/24 closest U11 evidence/page/report tests; 99/99 U11/browser/CAPTCHA regression envelope; dependency-light P0-A 65/65, P0-B 10/10, and P0-C 23/23; Ruff, compileall, and `git diff --check` pass. Production imports and dependency declarations were not changed. The verified U5d live DOM-card extraction path remains separate from U11 JSON-LD/report acceptance.
- `docs/U11_BROWSER_ENHANCEMENT_RESEARCH.md` records a separate future candidate: passive Playwright `console`/`pageerror`/`requestfailed` observation. That observer was not implemented in U11 and still requires an isolated compatibility slice; the research also records a Camoufox release-license metadata mismatch that must be resolved before redistribution.

## Accepted work unit U12 — additive passive browser diagnostics

- **Lifecycle status:** accepted on 2026-08-14 after explicit human authorization, fake-page/research-walker acceptance and all relevant offline source/browser/CAPTCHA tests.
- `utils/browser_diagnostics.py` introduces a dependency-light, passive observer for the existing page only. It attaches exactly `console`, `pageerror` and `requestfailed`; it never navigates, clicks, types, waits, changes page/context/browser settings or touches launch/profile controls. Each event kind is capped at eight observations.
- The observer records JSON-safe, bounded diagnostics only: normalized console level, sanitized location URL, redacted console/page-error/request-failure text, and sanitized failed-request URL. It never reads console arguments, response bodies, headers, cookies, storage, CAPTCHA payloads, HTML or screenshots. Sensitive assignments, including bounded nested percent-encoded forms, are replaced with `[redacted]` before the snapshot is returned.
- `CamoufoxResearchWalker.run` attaches the observer before its existing request/response capture, returns the sanitized snapshot as `ResearchWalkerResult.runtime_diagnostics`, and removes only its own handlers on every return path. Existing discovery output, navigation, waits, selectors, Camoufox/BrowserForge setup, persistent profile, proxy/GeoIP settings, human behavior and same-session manual challenge handoff remain unchanged.
- `utils/site_error_tracking.py` maps source-tagged console, page-error and failed-request observations into the existing error-summary path without changing legacy source defaults.
- Current deterministic evidence: direct observer/redaction/cap/JSON/site-error tests, direct walker snapshot/detach test and protected browser-context regression all pass. The complete offline browser/CAPTCHA/source-adapter/U11 envelope is 101/101 PASS. Ruff, compileall and `git diff --check` pass. No live source run, package installation, browser launch-option change, profile exposure, commit, push, PR, deployment or release occurred.

## Accepted work unit U13 — recorded-fixture launcher exposure

- **Lifecycle status:** accepted on 2026-08-14 after explicit human authorization, RED→GREEN verification, dependency-light regression, and independent read-only Standards/Spec reviews with no findings.
- **Frozen scope:** `docs/U13_RECORDED_FIXTURE_LAUNCHER_EXPOSURE_SPEC.md`.
- `recorded-legacy-fixture` is now one explicit launcher-visible `SourceKind.FIXTURE` profile. It has a fixed non-secret `fixture://recorded-legacy-products-v1` locator and two explicit recorded DOM/API sample nodes; the launcher still starts with a blank SourceProfile and blank CatalogNode selection.
- The existing `RecordedLegacyFixtureSourceAdapter` is registered only through `utils/source_adapter_tasks.py` in the selected local `source_adapter_collection` path. Each invocation receives a fresh fixed in-code document; collection passes through the existing local task and `ProductWorkspace` boundaries with exact safe provenance.
- Current deterministic evidence: launcher list/blank-state check; DOM path through the direct local task; API path through `DesktopLauncherController` and the real local subprocess; P0-A 65/65, P0-B 12/12 and P0-C 23/23; Ruff, compileall and `git diff --check` pass.
- No browser/API/network run, source discovery, optional dependency, live collection, cookies, credentials, proxy/session/profile material, CAPTCHA action, archive import, database migration, commit, push, PR, deployment or release occurred. U13 proves recorded local fixture exposure only; it is not evidence of live-source support.

## Closed — Stage 0A security and explicit-boundary stabilization

- **Lifecycle status:** closed on 2026-08-14 after final-current v4 deterministic verification and two independent hash-bound reviews: Standards `PASS — No findings`; Spec `PASS — No findings`.
- The frozen boundary contains 19 paths at branch `codex/p0b-challenge-handoff`, committed HEAD `7384328602249888d80f5a4631a4730d201ad4cc`; manifest SHA-256 is `38a405d15e7fa7f0cd982bde569259f3ee689ec58223e1a009aed1eadfcafe8a` and final identity verification found `0/19` mismatches.
- Stage 0A closes bounded repeated/malformed URL decoding, restricted artifact/evidence references, explicit live/task identities, pre-side-effect validation, safe manifest input, aggregate-only smoke logging, direct-runner/onboarding boundaries and strict catalogue-node identities.
- Final deterministic evidence: targeted `90/90`, dependency-light P0-A `88/88`, P0-B `12/12`, P0-C `23/23`, expanded contour `179/179`, scoped compileall/Ruff/diff checks and offscreen desktop smoke all passed.
- Full pytest remains unclaimed because inherited native Qt/PySide6 attempts crashed instead of returning assertion results. The broader worktree remains intentionally dirty and includes multiple historical/current slices.

## Closed — Stage 0B cumulative-WIP stabilization

### Outcome

The multi-stage dirty worktree was made reviewable without rewriting Git history: the deterministic inventory, exact 19-path Stage 0A boundary, aggregate-only `.runtime` count and active lifecycle documents were reconciled before Stage 1 implementation.

### Frozen boundary

- Initial inventory: 158 WIP paths = 51 modified, 14 renamed and 93 untracked.
- The 19 Stage 0A paths are all present; missing count is zero.
- Twenty-two `.runtime` paths are recorded only as an aggregate count; their names and contents are excluded.
- Stage 0B changes only this document, `docs/UNIVERSAL_PRODUCT_CATALOG_PLAN.md` and `docs/DECISIONS.md`. Production code, tests, CI, dependencies, runtime data and Git history are outside the slice.

### Completion evidence

- The three active documents agreed on Stage 0A closure, Stage 0B scope and the post-stabilization sequence.
- Pointer, whitespace and independent hash-bound documentation review gates passed.
- Stage 0B introduced no production, test, CI, dependency, runtime or live-source behavior and did not rewrite Git history.

## Closed — Stage 1 universal desktop workspace/export

- The launcher owns canonical `ProductWorkspace` state, missing-aware filtering, explicit product selection and explicit JSON export without inventing legacy supplier/field values.
- Worker/subprocess results are serializable; GUI-owned state and persistence remain GUI-thread-only.
- Deterministic acceptance and independent review passed; delivered commit: `291ba09b9af0aa42e66d1382a8e4a2e231cd60ae`.
- Browser/API execution, user-database migration and legacy report migration were excluded.

## Closed — Stage 2 local file picker and CatalogNode tree

- The local-file profile uses `QFileDialog` and a source-neutral tree populated only from a strictly inspected local JSON document; internal node IDs are not editable UI input.
- Labels and parent links are source-declared. Malformed hierarchy, restricted material, identity mismatch and noncanonical `file:` locators fail closed.
- Inspection and collection workers are state-neutral and JSON-safe; GUI callbacks own state application/persistence and stale-tree invalidation.
- Final evidence: 217 deterministic tests passed; immutable Standards review had no findings; immutable Spec review passed. Delivered commit: `4551b54b1f76ce316e259dd1a6b78bdb780ed297`.
- Full native Qt/PySide6 green status and live collection are not claimed.

## Active bounded candidate — U5 offline adapter-onboarding boundary

1. Map the retained optional browser capability to one explicit `SourceAdapter`/`SourceProfile` registration seam using deterministic fixtures or fake pages only.
2. Prove the profile is unreachable unless explicitly selected and that generic application/launcher modules contain no retailer, host, category, output-path or anti-bot default.
3. Keep browser launch, optional-dependency installation, live profile exposure and every live collection outside this offline slice.

## Future gated candidate — live SourceProfile exposure (not started; separate decision)

Any launcher-visible browser/API `SourceProfile` exposure and every new live collection run require a separately frozen scope and explicit human decision. They are not part of U13 acceptance.

## Sequenced follow-up

1. **U5 offline adapter onboarding:** define and verify one explicit optional-browser adapter/profile registration boundary without browser launch or live access.
2. **Future live exposure:** make a separate decision before any launcher-visible live browser/API `SourceProfile`.
3. **Future live capability:** browser handoff and same-session manual CAPTCHA input remain optional capabilities; any new live collection run requires a frozen plan and explicit live gate.
4. **U6 release hardening:** replace stale retailer-first demos/CI surfaces and archive legacy parsers only after reference and adapter-replacement evidence.

## Validation policy

Use deterministic fixture/local-file tests for CI. A live source test is manual, separately approved and never the generic acceptance criterion.
