# ParserRIba Roadmap V1

Date: 2026-05-31

## Purpose

This roadmap defines delivery order for the current local-first ParserRIba
stage. Layer boundaries live in `docs/TARGET_ARCHITECTURE.md`. Current state and
cleanup evidence live in `docs/PROJECT_STATE.md` and
`docs/WORKSPACE_CLEANUP_INVENTORY.md`.

## Product Direction

ParserRIba v1 is a local Windows desktop program. The canonical architecture is:

`Launcher -> Task Orchestrator -> Browser/Discovery Core -> Store Adapter -> Product Core -> Filter Core -> Report Core -> Storage/Profile Core`

The canonical user workflow is:

`Исследование -> Каталог -> Товары -> Отчёт`

The product should let a non-technical user:

1. enter a store URL;
2. run site/catalog research;
3. see a discovered catalog tree;
4. select any needed catalog nodes;
5. collect full product cards from selected nodes;
6. narrow the product workspace through dynamic filters;
7. select exact products;
8. choose report columns;
9. export Excel/JSON artifacts;
10. keep the site profile for future runs and price history.

## Current Priorities

1. Keep Pyaterochka stable as the first runtime-ready adapter.
2. Keep runtime local: Python, Camoufox, SQLite, JSON and Excel.
3. Finish Launcher V3 around catalog tree, product workspace, dynamic filters,
   selected products and report-column selection.
4. Improve product-card extraction before adding more decorative UI.
5. Make StoreProfile the central owner for per-site catalog/product/filter/report
   state.
6. Archive legacy parser/strategy/policy code in verified slices.
7. Add additional stores only through discovery-first onboarding after
   Pyaterochka is useful end to end.

## Runtime Rules

- Browser runtime is Camoufox through async Playwright-compatible APIs.
- Store-specific URL/selectors/route markers belong in `knowledge_base/`.
- Pyaterochka protected mechanics are preserved through browser/store adapter
  contracts, not by keeping the old parser stack as product runtime.
- Dynamic filters are derived from collected product data and mapped site facets.
- Missing product fields do not silently exclude products unless strict mode is
  explicitly enabled.
- Report export uses selected product IDs first; otherwise it uses the current
  filtered product workspace.
- Report columns are selected by the user from base fields, useful raw product
  fields and discovered filter fields.

## Delivery Order

1. Keep the Launcher V3 task/state contracts stable.
2. Strengthen product collection from selected catalog node URLs.
3. Strengthen product raw-field extraction and normalization.
4. Strengthen mapped site facets and local filter application.
5. Persist filter presets and report-column presets into StoreProfile.
6. Add price-history snapshots to the local storage/profile layer.
7. Remove deeper legacy bridge files only after compatibility/build/test
   references are replaced.
8. Add the next runtime-ready store after Pyaterochka flow is stable.
9. Start packaging/installer/release work only after the desktop product is
    genuinely useful.

## Deferred

- Paid scraping/captcha/browser services.
- Cloud LLM services.
- Mandatory remote backend.
- Multi-user dashboard.
- Server-side worker fleet.
- Installer/update delivery before launcher MVP quality.

## Validation

Use the commands in `docs/NEXT_STEPS.md` after each implementation or cleanup
slice.
