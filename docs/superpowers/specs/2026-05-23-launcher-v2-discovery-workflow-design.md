# Launcher V2 Discovery Workflow Design

Date: 2026-05-23

## Purpose

Launcher V2 turns the current one-screen launcher into a workflow built around
the actual ParserRIba product goal:

1. research a store website;
2. show the full discovered catalog;
3. let the user choose any number of categories and subcategories;
4. collect full product cards from the selected parts of the catalog;
5. derive filters dynamically from collected product fields;
6. let the user choose exact products;
7. build Excel/report output.

The launcher must stay understandable for a non-technical Russian-speaking user
and must not expose internal evidence/classifier details unless a later
developer diagnostic mode explicitly asks for it.

## Current Problems

- The launcher shows a flat result table, not a catalog workflow.
- The full catalog can now be returned as `full_catalog_tree` and
  `full_catalog_links`, but the visible UI does not make it clear enough.
- For Pyaterochka, the first discovery pass currently finds mostly top-level
  catalog URLs. Deep branches are not visible because the walker has not yet
  opened every section and extracted breadcrumbs, listing API metadata,
  subcategory links or site-provided facets.
- Category selection is visually awkward and behaves like a small list, while
  the product goal requires selecting any number of tree nodes.
- Filter UI is hardcoded into separate fixed blocks. Future stores and full
  product-card extraction will create fields that are not known in advance.
- Long browser tasks have been moved to a background thread, but the visible
  flow still does not show enough progress or next-step guidance.

## Design Direction

Use a guided tabbed workflow instead of one dense form. The tabs are:

1. `Исследование`
2. `Каталог`
3. `Товары`
4. `Фильтры`
5. `Отчёт`

The same `DesktopLauncherController` remains the owner of state transitions.
The PySide6 shell renders widgets and delegates actions. Runtime work continues
through local tasks; the UI must not directly call parser scripts, Camoufox, or
store backends.

Launcher V2 is a multi-site profile manager, not a Pyaterochka-specific
launcher. The central product object is `StoreProfile`: one profile per website
or store domain. Pyaterochka is one existing profile/adapter and one legacy
reference implementation, not the architecture center.

## Multi-Site Store Profile Model

Launcher V2 must support many sites over time:

- one website/domain creates one store profile;
- profiles do not share catalog trees, selected categories, product workspaces,
  filters, diagnostics or price history;
- the last active profile may open by default;
- the user can switch profiles without re-entering old URLs;
- a newly entered URL either opens an existing matching profile, updates that
  profile, or creates a new profile;
- profile data remains local-first in SQLite and JSON snapshots, but the schema
  must stay migration-friendly for a later Postgres backend.

Each `StoreProfile` keeps:

- site URL and display name;
- current status: working, partial, needs operator, blocked or failed;
- discovered catalog tree and full catalog links;
- selected catalog nodes;
- route/API hints and payload evidence refs;
- browser/session strategy notes;
- region/proxy/challenge diagnostics without secrets;
- dynamic filters found from product data;
- product collection history and last successful run time;
- price-history availability for future reports.

Profile settings should be visible through a `Профиль магазина` panel or
dialog, not as noise on the first screen. The main flow stays simple, but the
operator can inspect and adjust profile-level settings when needed.

### Network And Proxy Settings

Proxy controls are useful for protected stores, but they should start as an
advanced profile section:

- mode: auto, no proxy, use configured proxy;
- last network/proxy status;
- region/geo mismatch hints when known;
- challenge/403/captcha history;
- proxy identity shown only as mask/hash/status.

Proxy credentials, cookies, captcha tokens and auth headers must never be
stored in profile snapshots or committed artifacts.

## Pyaterochka Runtime Boundary

The existing Pyaterochka runtime must not be carried forward as the generic
Launcher V2 discovery engine.

It remains in two compatibility-only roles:

1. source material for extracting proven Camoufox launch, RU proxy, GeoIP,
   persistent profile, human-like behavior, anti-bot diagnostics and
   interception mechanics into target cores;
2. temporary store-specific adapter until the new store-neutral pipeline can
   collect full products with the same reliability.

The old parser/runtime path is not a product runtime and should be archived
after useful mechanics are extracted.

Launcher V2 must evolve around store-neutral contracts:

- store profile;
- catalog/deep research;
- selected catalog nodes;
- product workspace;
- dynamic filter facets;
- report input.

Useful Pyaterochka mechanics may be extracted into reusable browser/session or
protection modules only when they fit those contracts. The new launcher,
catalog discovery and filter architecture must not depend on embedding the old
Pyaterochka runtime.

## Tab 1: Исследование

Purpose: run store research and create/update the local store profile.

Visible controls:

- site URL input;
- shop selector;
- intent selector;
- headless/manual wait/research mode controls;
- primary button `Исследовать сайт`;
- progress/status area with phase messages.

Visible results:

- full catalog count;
- selected intent category count;
- challenge/blocked/partial warning when present;
- profile id/version;
- clear next-step hint: `Перейдите в Каталог и выберите разделы`.

Data used:

- `catalog_discovery`;
- `full_catalog_tree`;
- `full_catalog_links`;
- `profile_notes`;
- `phase_events`.

## Tab 2: Каталог

Purpose: show the full catalog tree and let the user select any number of
categories/subcategories.

Visible controls:

- tree widget with checkboxes;
- columns: section name, URL, child count;
- buttons:
  - `Выбрать всё`;
  - `Снять выбор`;
  - `Исследовать выбранные глубже`;
  - `Собрать товары по выбранным`;
- compact selected-count label.

Selection behavior:

- no categories are pre-selected after research;
- any number of tree nodes can be checked;
- checking a parent does not automatically hide or overwrite child choices;
- selected nodes are stored as stable node records, not just display names:
  - `node_id`;
  - `name`;
  - `url`;
  - `parent_ids`;
  - `source`.

Deep research behavior:

- `Исследовать выбранные глубже` opens selected category URLs through the same
  Camoufox discovery path.
- It tries to extract:
  - child category links;
  - breadcrumbs;
  - listing API route hints;
  - pagination hints;
  - site-provided facets/filters if visible before product collection.
- Results merge back into the active profile and update `full_catalog_tree`.

Important Pyaterochka note:

Pyaterochka top-level category URLs are often flat. If the site does not expose
URL hierarchy, the first tree will be `Каталог -> 140 sections`. Deeper
branches require the second pass over selected/all top-level sections.

## Tab 3: Товары

Purpose: collect and display products from selected catalog nodes.

Visible controls:

- button `Собрать товары`;
- product table;
- select all / clear product selection;
- open JSON/output folder actions.

Product table columns:

- category;
- product name;
- brand;
- supplier/producer/vendor;
- country/place when available;
- subtype/style;
- price;
- stock;
- URL.

Behavior:

- products are collected only from checked catalog nodes;
- multiple selected categories are processed in sequence through existing local
  task/export contracts;
- no direct simplified Pyaterochka scraping path is added;
- existing Pyaterochka export can remain a temporary adapter behind the generic
  selected-node product collection contract;
- collected products are persisted to SQLite and JSON as they are today;
- the table supports selecting exact products for the final report.

## Tab 4: Фильтры

Purpose: build one dynamic scrollable filter panel from actual collected
product fields.

Visible controls:

- one scroll area;
- one collapsible/sectioned filter group per field;
- reset filters button;
- strict-missing toggle;
- price/stock controls.

Filter source:

- normalized product fields:
  - category;
  - brand;
  - supplier;
  - producer;
  - vendor;
  - country;
  - subcategory/style;
  - alcohol type;
  - sugar class;
  - color;
- raw product fields from `raw_data` when they have useful repeated values.

Dynamic filter output:

- known normalized fields keep friendly Russian labels;
- unknown fields appear under `Дополнительно найденные фильтры`;
- every filter option shows a count;
- missing fields do not exclude products by default;
- strict mode may exclude missing values when the user enables it.

The old fixed filter boxes are replaced by the dynamic panel after product
collection. They may remain internally as compatibility mapping during the
transition, but not as the final UI concept.

## Tab 5: Отчёт

Purpose: build the final Excel/report from selected or filtered products.

Visible controls:

- selected product count;
- active filter summary;
- `Собрать Excel`;
- `Открыть Excel`;
- `Открыть папку`;
- `Открыть JSON`.

Behavior:

- if exact products are selected, the report uses those products;
- otherwise it uses currently filtered products;
- report generation continues through `store_report_export`;
- the report summary returns to the launcher and remains visible.

## State Model Additions

Launcher state should distinguish:

- `full_catalog_tree`: full discovered tree;
- `full_catalog_links`: flat full URL list;
- `selected_catalog_nodes`: checked tree nodes for product collection;
- `product_workspace`: current collected product set metadata;
- `dynamic_filter_facets`: filter fields derived from product data;
- `selected_dynamic_filters`: current user filter choices;
- `selected_product_ids`: exact product selection for report.

The old `selection.categories` can remain as a compatibility field during the
transition, but V2 should use selected catalog nodes as the canonical source for
collection.

## Data Flow

Research flow:

`Исследовать сайт -> site_onboarding_discovery -> full_catalog_tree/full_catalog_links -> Каталог tab`

Deep research flow:

`Checked catalog nodes -> deep catalog research task -> merged profile -> updated full_catalog_tree`

Product flow:

`Checked catalog nodes -> existing export tasks -> SQLite/JSON -> product table -> dynamic filters`

Filter flow:

`Collected product records -> dynamic facet builder -> Фильтры tab -> filtered product table`

Report flow:

`selected_product_ids or filtered product set -> store_report_export -> Excel/report summary`

## Error Handling

- Browser/challenge/proxy errors must not freeze the UI.
- Partial research stays visible and actionable.
- If deep research fails for one branch, the branch gets a warning but other
  branches remain usable.
- If no products are collected, the UI explains whether the cause is:
  - no selected categories;
  - blocked/challenge;
  - empty product payload;
  - parser/runtime error.
- Captcha remains manual; no paid captcha or cloud browser services are added.

## Implementation Slices

### Slice 1: UI Shell Restructure

Create the tabbed shell and move existing controls into the new tabs without
changing runtime behavior.

### Slice 2: Store Profile Surface

Add the visible profile selector/panel and make `StoreProfile` the launcher
context for catalog, products, filters and reports.

### Slice 3: Catalog Tree Selection

Render `full_catalog_tree` in a checkbox tree widget and store checked nodes.
Allow any number of categories/subcategories.

### Slice 4: Product Collection From Selected Nodes

Convert checked nodes into the existing export task inputs. Preserve the
temporary Pyaterochka adapter only behind the generic collection contract.

### Slice 5: Dynamic Filter Panel

Build dynamic facets from collected product records and render them in one
scrollable filter area.

### Slice 6: Deep Category Research

Add a local task for deeper selected-node discovery and merge the results into
the active profile/tree.

## Non-Goals For This Spec

- No new paid scraping/captcha/cloud browser services.
- No full replacement of the Pyaterochka product adapter in the first UI slice.
- No server/backend/Postgres migration.
- No installer redesign.
- No promise that every site will expose true nested category structure in the
  first pass; deep research is the mechanism for improving it.

## Acceptance Criteria

- The launcher no longer looks like one overloaded form.
- A user can see the full discovered catalog separately from the chosen intent
  categories.
- A user can select any number of catalog nodes.
- The product collection action uses the selected nodes.
- Filters appear dynamically from collected product/card data in one scrollable
  panel.
- The report action uses selected products or filtered products.
- Browser work does not freeze the launcher window.
- All visible new workflow labels are in good Russian.
