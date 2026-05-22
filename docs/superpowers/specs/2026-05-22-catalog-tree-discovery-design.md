# Catalog Tree Discovery Design

Date: 2026-05-22

## Purpose

This document fixes the design of the launcher action `Исследование`.

The goal is to build a reusable `catalog tree discovery` core that can:

- open a store site through the project browser/runtime path;
- discover catalog trees and menu structures, not just product links;
- validate which branches are real product listings;
- persist a reusable store profile with discovery evidence;
- feed the launcher with a simple Russian-language category tree for users.

This design is intentionally broader than Pyaterochka-only logic, but
Pyaterochka remains the first protected-store backend and the first runtime
that must keep working end-to-end.

## Product Goal

The launcher should support this user flow:

1. The user opens the launcher.
2. The user enters a store URL.
3. The user presses `Исследование`.
4. ParserRIba opens the site through the protected browser/runtime path.
5. ParserRIba discovers the menu, category tree, subcategory tree, and useful
   API/route evidence.
6. ParserRIba creates or updates a local store profile from that run.
7. The launcher shows a clean Russian category tree.
8. The user chooses the categories they need.
9. ParserRIba later collects products from the selected categories only,
   except for limited strategy-driven side branches needed for validation or
   route understanding.
10. The launcher builds filters from the real collected products.
11. The user selects exact products and exports a report or Excel table.

`Исследование` itself does not need to collect the full product catalog in the
first version. Its first responsibility is discovery and validation of the
catalog structure.

## Non-Goals For V1

The first version of `Исследование` should not:

- automatically solve captcha;
- use paid anti-bot, browser, or scraping APIs;
- depend on cloud services or hosted LLMs;
- expose internal strategy/debug data directly to simple users;
- fully generalize every store-specific filter derivation problem.

Captcha remains manual. Browser/runtime logic stays local and free.

## Design Principles

1. Keep user UX simple, keep the core rich.
2. Separate discovery of the catalog tree from product collection.
3. Preserve Pyaterochka runtime mechanics instead of creating a simplified
   launcher-specific scraping path.
4. Store evidence and provenance now, because strategy work will need it later.
5. Keep storage replaceable so the project can move to a stronger database
   later without rewriting the discovery core.

## User Experience

### Launcher Action

The launcher action is named `Исследование`.

Default behavior:

- show phased progress;
- stream found categories in real time;
- keep all visible UI text in good Russian;
- normalize ugly site labels before presenting them to users.

Optional mode:

- allow a simplified `single run -> final result` mode for users who do not
  want live streaming updates.

### What The User Sees

The user should see only:

- the current research phase;
- the current status;
- the primary discovered tree;
- brief understandable warnings such as:
  - `нужна ручная проверка`;
  - `частично исследовано`;
  - `обнаружена защита`;
- the latest current site profile.

The user should not see raw provenance blobs, internal evidence graphs,
technical API markers, or low-level anti-bot metadata unless a future debug UI
explicitly requests it.

### Category Labels

The launcher should show normalized Russian labels by default.

The original site labels must still be stored in the core and be retrievable as
secondary data, for example in details or debugging views.

### Conflicting Trees

If the core finds several competing trees, such as:

- header menu;
- side navigation;
- API tree;
- burger menu;

then:

- the core stores all candidate evidence;
- the launcher shows one merged primary tree;
- conflicting nodes can be marked as uncertain in a user-friendly way;
- alternative sources stay available for later strategy work.

## Discovery Core

### Name

The new subsystem should be treated as a dedicated core:

- `catalog tree discovery core`

### Responsibility

Its job is to discover and validate the navigable catalog structure of a site,
not to collect the final report data.

### Inputs

- `site_url`
- optional `shop` hint
- runtime mode settings
- headless mode
- proxy/session options
- manual challenge mode
- timeouts

### Outputs

- normalized primary catalog tree
- discovery graph with evidence and provenance
- per-node validation state
- store profile snapshot
- launcher-facing research summary

## Execution Pipeline

The `Исследование` pipeline should have these phases.

### Phase 1: Browser Startup

Use the existing protected runtime path:

- Camoufox
- proxy handling
- GeoIP
- persistent profile/session reuse
- human-like behavior
- anti-bot detection

Pyaterochka must reuse the current runtime path rather than a separate launcher
path.

### Phase 2: Surface Collection

Collect every plausible catalog signal from the page:

- DOM navigation menus
- burger and overlay menus
- breadcrumbs
- anchor links that look like category paths
- inline JSON blobs
- network requests and responses
- category-like route patterns
- page transitions caused by real browsing

This phase should produce candidate nodes and candidate relations, not yet the
final tree.

### Phase 3: Adaptive Tree Expansion

Expansion should be adaptive, not fixed-depth.

Rules:

- go deeper while the core keeps finding credible category/listing signals;
- stop when branches become repetitive, noisy, blocked, non-product, or empty;
- allow limited strategy-driven side exploration when needed to understand the
  real tree shape or listing route.

This implements the approved mode:

- selected-category-first later for product collection;
- strategy-aware discovery now for tree validation.

### Phase 4: Listing Validation

For each likely category node, run a short validation step:

- open the target;
- check whether it behaves like a product listing;
- wait briefly for DOM/network signals;
- record route/API hints;
- classify outcomes such as:
  - real listing;
  - menu-only page;
  - promo page;
  - PDF/flipbook;
  - region gate;
  - challenge/captcha;
  - unknown.

### Phase 5: Profile Persistence

Persist:

- the primary tree;
- evidence graph;
- node validation results;
- run diagnostics;
- route/API hints;
- profile metadata and history.

### Phase 6: Launcher View Build

Convert the profile into a launcher-safe view:

- current phase status
- simple Russian labels
- primary category tree
- brief warnings
- category stream for live mode

## Manual Challenge Handling

If captcha or another challenge appears:

1. pause the run and keep the browser open;
2. allow manual solving;
3. resume automatically if solved within the configured wait window;
4. if not solved in time, save partial state and finish as partially explored.

The timeout strategy should match the Pyaterochka parser behavior as closely as
reasonable.

## Discovery Graph Model

Internally the core should keep a richer graph than the launcher shows.

### Discovery Node

Each node should eventually support fields in this spirit:

- stable node id
- normalized Russian label
- original site label
- canonical URL
- candidate URLs
- parent links
- child links
- discovery source:
  - `dom`
  - `network`
  - `mixed`
  - `manual_confirmed`
- validation state
- listing confidence
- route/API hints
- protection signals
- manual step seen
- last seen run id
- raw evidence references

The launcher does not need to expose all of this.

### Discovery Edge

Edges should capture the relationship between nodes:

- parent-child
- cross-link
- duplicate candidate
- alternative-source confirmation

### Why Rich Nodes Matter

This is not overengineering. It prevents later rewrites when the project adds:

- store-specific strategies;
- route selection logic;
- retry policies;
- conflict resolution;
- profile comparison across runs.

## Store Profile

### What The Profile Is

A store profile is the persisted result of repeated research runs for one site.

It should describe:

- the current best known tree;
- historical profile versions;
- known route/API markers;
- validation outcomes by node;
- discovered language/label normalization;
- strategy hints learned from observation.

### What The User Sees

Only the latest active profile.

### What The Core Keeps

- full history of profile versions;
- enough historical evidence to compare changes in menu/tree structure later.

### Privacy And Safety

Profiles must not store:

- raw proxy credentials;
- cookies;
- captcha tokens;
- auth headers;
- secrets from `.env`.

## Storage Design

Storage should be replaceable.

### Current Choice

Use:

- `SQLite` as the main local operational store;
- JSON snapshots in `data/` for manual inspection and debugging.

### Required Abstraction

Define repository-style boundaries for the profile domain so the project can
move later to a stronger database without changing the discovery core itself.

Conceptually:

- `ProfileRepository`
- `ProfileHistoryRepository`
- `ProfileSnapshotWriter`

The names can change, but the separation should remain.

## Relationship To Product Collection

`Исследование` ends with a validated tree and a store profile.

Product collection starts after the user selects categories.

Collection rules:

- default scope is only the categories selected by the user;
- the runtime may explore adjacent branches only when needed for strategy or
  validation reasons;
- collected products become the source of filter derivation.

## Filters After Collection

Filters should be built only from real collected product data, not from KB
guesses.

### Two-Layer Filter Model

Layer 1: common filters

- category
- subcategory
- brand
- producer
- manufacturer
- supplier
- price range
- in-stock state

Layer 2: additionally found filters

- store-specific or product-family-specific facets discovered from raw data;
- examples for wine:
  - color
  - sugar class
  - alcohol type
  - style
- examples for fish:
  - species
  - cut/form
  - processing style

### Launcher Presentation

The special filter block should be presented as:

- `Дополнительно найденные фильтры`

This makes it obvious to the user that new meaningful filters appeared after
the data was collected.

### Future Extension

Later the project can add a dedicated filter-derivation core that builds richer
special filters from raw product attributes. This is realistic and should fit
naturally if the current design keeps common filters and special filters
separate.

## Final Product Selection

After filtering, the launcher should support selecting exact products before
report export.

That implies:

- a collected product workspace for the selected categories;
- filtered result views;
- explicit selected product IDs or equivalent stable selection keys.

Report export should be able to target:

- all filtered products;
- or only explicitly selected products.

## Russian UI Rule

All user-facing launcher text for this flow must be in good Russian:

- button labels
- statuses
- progress phases
- hints
- warnings
- conflict messages
- filter names

Avoid raw technical English unless the user is explicitly in a diagnostic mode.

## Proposed Phase Labels For UI

Candidate phase labels:

- `Открытие сайта`
- `Поиск структуры каталога`
- `Проверка разделов`
- `Сбор признаков и маршрутов`
- `Сохранение профиля`
- `Подготовка дерева`

These labels can be tuned later, but the Russian-language rule is fixed.

## First Implementation Boundary

The first implementation slice should focus on:

1. discovery pipeline for `Исследование`;
2. adaptive category/menu tree discovery;
3. per-node validation;
4. store profile persistence with history;
5. launcher-facing live progress and streamed categories;
6. simple/quiet mode toggle;
7. no automatic captcha solving.

This is enough to create a real reusable discovery core without expanding
prematurely into every later strategy system.

## Open Questions Already Resolved

These decisions are already fixed for the next plan:

- default launcher mode is live phased progress with streaming categories;
- a simpler final-result mode also exists;
- UI shows only the latest profile;
- history stays inside the core;
- category labels are normalized to Russian by default;
- original labels are retained internally;
- conflicting trees are merged for the user but preserved in the core;
- challenge handling is pause/resume with timeout and partial persistence;
- filters use a common layer plus `Дополнительно найденные фильтры`;
- product collection is selection-first and strategy-aware.

## Next Step

The next artifact should be an implementation plan that maps this design onto:

- new discovery-core modules;
- profile models and repositories;
- launcher progress/result models;
- tests for adaptive tree discovery and profile persistence;
- integration of the `Исследование` button with the new pipeline.
