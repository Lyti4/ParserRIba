# ParserRIba Architecture Decisions

**Vocabulary:** `CONTEXT.md`
**Active plan:** `docs/UNIVERSAL_PRODUCT_CATALOG_PLAN.md`

## Accepted decisions

### ADR-001 — Universal product boundary

ParserRIba serves any products from explicit sources. Retailers, categories, product classes and URLs are adapter/profile inputs, not global defaults.

### ADR-002 — SourceAdapter seam

The generic caller crosses one collection seam: `collect(CollectionRequest) -> CollectionResult`. Source-specific discovery, browser/API behavior and normalization mechanics stay inside a SourceAdapter.

### ADR-003 — Explicit selection and provenance

Collection requires one SourceProfile plus explicit CatalogNodes or named input set. Every product observation retains safe source, adapter, run and selection provenance.

### ADR-004 — Local-first deterministic baseline

Fixture and local-file workflows are the mandatory development/CI baseline. Browser/API adapters are optional, opt-in capabilities.

### ADR-005 — Preserve observations; normalize without invention

ProductObservations and NormalizedProducts are distinct. Missing data remains missing. Product-type-specific schemas, filters and reports are optional capabilities.

### ADR-006 — Manual challenge only

CAPTCHA is never automatically solved or bypassed. A separate same-session manual handoff may exist for an explicitly selected browser adapter.

### ADR-007 — Existing retailer code is adapter/reference material

Pyaterochka-specific runtime, fixture, source profile and tests are retained as optional adapter/reference evidence during migration. They cannot define product-facing defaults or generic imports.

### ADR-008 — Documentation and history

One active plan and glossary guide the product. Completed or superseded plans move to `archive/project_history/`; archive remains non-runtime historical evidence. Knowledge-base profiles remain until reference review proves a safe removal.

### ADR-009 — Strict explicit local JSON import

`local-json-file-v1` is a deterministic `file:///`-only input adapter. Its JSON v1 envelope, node records and product records have strict allowlists; all imported records are validated through the source-neutral contracts before explicit-node filtering. Extensible product data remains in safe `source_fields` and `attributes`, never adapter/root proxy, browser, session or credential configuration.

### ADR-010 — Declared launcher profile catalog and explicit task dispatch

The launcher and local source task share a small declared profile catalog for fixture and file collection. The UI may list choices but starts blank; the controller rejects blank profile/node input before dispatch. The file profile accepts only canonical hostless absolute `file:///.../*.json` input and the public task wrapper validates the complete request before spawning. It passes a run identifier, selected profile ID, validated locator and explicit node IDs to the named local `source_adapter_collection` task. That task constructs the source-neutral request and delegates only through the registry; product intent/category cannot select an adapter. Legacy research controls remain compatibility-only and default-free until their optional capabilities migrate; blank/unknown legacy intent is fail-closed before browser or task work.

### ADR-011 — Canonical local ProductWorkspace and explicit JSON export

A source-neutral `ProductWorkspace` is the post-collection aggregate for one or more explicit `CollectionResult` values. It stores observations, normalized products and declared fields separately, retains matching provenance, exposes declared facets plus scalar leaves from nested attributes/source fields, and returns filtered/export projections without mutation. Repeated declared field IDs must agree; an explicit filter must contain at least one facet, and missing values remain visible unless strict filtering is selected. Its local persistence format is strict `parserriba-product-workspace-v1`; generic JSON export requires exactly one explicit product list, non-empty filtered selection, or whole-workspace selection and has opt-in provenance columns. The U3 source task may publish a workspace artifact only below its task-root `workspaces/` directory using a filename-safe run ID; launcher UI, user-database migration, browser/API collection and legacy report migration remain separate decisions.

### ADR-012 — Fail-closed public source boundaries

All public locator, artifact/evidence, task, live-runner and launcher boundaries reject malformed, repeated/excessive encoded, credentialed, restricted operational or ambiguous material before output directories, adapters, runners, research, logging, manifests or persistence. Live source URL, SourceProfile, CatalogNode, collection-run and runner identities are explicit and have no retailer/category fallback. Durable manifests are reconstructed only from validated contracts; rejected raw input is not reflected in public errors or logs. Stage 0A final-current v4, bound to manifest SHA-256 `38a405d15e7fa7f0cd982bde569259f3ee689ec58223e1a009aed1eadfcafe8a`, is the accepted evidence boundary for this decision.

### ADR-013 — Stabilize cumulative WIP before the next product slice

The current dirty worktree contains multiple historical/current slices and is not treated as one release unit. Stage 0B records a deterministic aggregate-safe inventory, preserves the exact 19-path Stage 0A boundary, synchronizes active lifecycle documents and defines delivery sequencing without rewriting Git history or changing production behavior. Historical U5–U13 work-unit/receipt labels are not product delivery phases and do not close product Phase U5 or U6. Commit/branch splitting remains a separate Git gate. Stage 1 universal desktop export may start only after Stage 0B acceptance; live browser/API SourceProfile exposure and every live collection remain separately frozen and approved.

## Open decisions

- launcher integration of explicit `ProductWorkspace` selection/filter state with the source-neutral export seam (Stage 1);
- live adapter onboarding/approval process (U5);
- retirement strategy for the legacy CLI/parsers after source-neutral paths exist (U6).
