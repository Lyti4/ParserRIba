# ParserRIba Product Glossary

This glossary defines the universal product-catalog vocabulary. It describes product meaning, not implementation.

## Product boundary

ParserRIba is a local-first desktop program for collecting, comparing, filtering and exporting **any products** from explicit user-selected sources. A retailer, category and product type are inputs, not product defaults.

## Core terms

### SourceProfile

A local, user-visible record that identifies one product source and its accumulated non-secret evidence. A source can be a deterministic fixture, a local file, a website, an API or a future adapter type.

A SourceProfile owns its display name, source locator, discovery state, catalog snapshot, selected nodes, collection history, diagnostics, and artifact references. It does not store credentials, cookies, CAPTCHA tokens, raw proxy values or browser-profile data.

`StoreProfile` is the current implementation-era name for a website-oriented SourceProfile. New contracts use `SourceProfile`; migration keeps legacy compatibility explicit.

### SourceAdapter

An adapter that supplies one source-specific implementation behind the generic source seam. It may discover catalog nodes, collect product observations, normalize fields and describe recoverable limitations. It does not decide user selection or introduce global defaults.

A source adapter is classified as one of:

- **fixture** — deterministic, no-network test data;
- **file** — user-provided local structured data;
- **browser** — optional local browser collection;
- **API** — optional confirmed public or permitted API collection.

### CatalogNode

One selectable position in a source catalogue. It has a stable source-scoped identity, display name, optional parent identity, locator/evidence reference and selection state. Collection uses only nodes explicitly selected by the user or explicitly supplied by an import request.

### CollectionRequest

A request bound to exactly one SourceProfile and its explicit CatalogNodes. It may include source-specific runtime settings, but has no implicit retailer, URL, category or product-type fallback.

### ProductObservation

An immutable source record captured during one collection run. It keeps source fields and provenance even when normalization is incomplete or ambiguous.

### NormalizedProduct

A product projection used for cross-source filtering and export. Its stable core is intentionally small: identity, name, category when known, price when known, availability when known, brand/supplier/country when known, and extensible attributes. Missing information remains missing; it is never invented from a product type or source name.

### Provenance

The evidence required to interpret a ProductObservation or NormalizedProduct: SourceProfile identity, adapter identity/version, collection run identity, selected CatalogNode identity, observed timestamp, locator or safe artifact reference, and transformation status. Provenance is not a credential store.

### ProductWorkspace

A non-destructive local aggregate for one or more explicit collection results and SourceProfiles. It keeps observations, normalized products, declared fields and provenance separate from projections. Filtering changes a view/selection, not the original observations.

### FieldDefinition

A normalized or discovered product field with type, display label, availability and optional facet behavior. Fish, wine and other domain-specific fields become optional FieldDefinitions, not global model requirements.

### Export

A user-requested local artifact produced from an explicit product selection or filtered ProductWorkspace. The current generic form is versioned JSON; format does not define the source model. Excel-compatible tables remain an optional/legacy projection, not a generic source requirement.

## Invariants

1. The product core has no mandatory retailer, category, product type, URL or browser backend.
2. Source-specific rules live in the relevant SourceAdapter/profile, not in the launcher, generic exporter or generic filter core.
3. Every collection has explicit source and selection provenance.
4. A missing field is represented honestly; it is not silently mapped, inferred or discarded.
5. A CAPTCHA is never solved automatically. Manual human action is an optional same-session capability, never the default collection path.
6. Network/browser access is opt-in. Fixtures and local files are the deterministic default for tests and development.
