# Launcher Discovery-First Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the desktop launcher around the user’s required site-first workflow: research store -> choose discovered sections -> collect products -> narrow selection -> build report.

**Architecture:** Keep the current local task/runtime stack, but change the launcher contract from category-first fallbacks to discovery-first state. The launcher must treat site research as the first-class source of sections and must stop pre-populating category choices from KB/backend defaults before research happens.

**Protected Pyaterochka invariant:** The launcher must preserve the existing Pyaterochka parser mechanics. Product collection for Pyaterochka must continue through the local task/backend path that uses Camoufox configuration, RU proxy/GeoIP, persistent profile/session reuse, human-like behavior, safe network/API interception, API-first candidate extraction, DOM/card fallback, and anti-bot/proxy/error reporting. Do not add a separate simplified Pyaterochka scraping path inside the launcher.

**Target product flow:** A user enters a store URL, clicks research, ParserRIba discovers catalog/category/API evidence through the browser/runtime, creates or updates a local store profile, shows discovered categories and subcategories, collects full product cards only for selected categories, derives filters from those collected products, lets the user select exact products, and exports Excel/report output for that selected set.

**Tech Stack:** PySide6, local launcher controller/state models, local task adapter/registry, site onboarding runtime, SQLite, openpyxl.

---

## File Map

- `docs/LAUNCHER_ARCHITECTURE.md`
  - explicit architecture map and stage flow for launcher work.
- `docs/NEXT_STEPS.md`
  - active execution track pointer to this plan.
- `docs/ROADMAP_V1.md`
  - high-level launcher contract updated to discovery-first wording.
- `launcher/desktop_launcher.py`
  - shell wiring and category refresh behavior.
- `launcher/desktop_window_sections.py`
  - user-facing action labels.
- `launcher/desktop_action_state.py`
  - stage-aware button enable rules.
- `launcher/desktop_controller.py`
  - launcher state transitions and task sequencing.
- `launcher/desktop_controller_helpers.py`
  - staged category/result helper logic.
- `launcher/desktop_view_helpers.py`
  - stage-aware summary/caption text.
- `utils/launcher_task_controller.py`
  - launcher-facing task semantics.
- `utils/site_onboarding.py`
  - category discovery and onboarding result semantics.
- `utils/onboarding_storage.py`
  - local store profile/session persistence.
- `utils/product_storage.py`
  - collected product state used for filters and reports.
- `utils/report_filter_facets.py`
  - filter values derived from collected products.
- `tests/test_desktop_launcher.py`
  - shell-level behavior and label expectations.
- `tests/test_desktop_launcher_controller.py`
  - staged controller behavior.
- `tests/test_desktop_view_helpers.py`
  - staged result rendering.

## Task 1: Freeze The Architecture Contract

**Files:**
- Create: `docs/LAUNCHER_ARCHITECTURE.md`
- Modify: `docs/ROADMAP_V1.md`
- Modify: `docs/NEXT_STEPS.md`

- [ ] Document the launcher layers and stage flow in one explicit architecture file.
- [ ] Update roadmap wording from generic onboarding/category flow to discovery-first launcher flow.
- [ ] Point the active next steps at this staged launcher rebuild.
- [ ] Document the protected Pyaterochka runtime invariant: launcher controls the flow, but collection still uses the existing Camoufox/proxy/GeoIP/human-behavior/interception backend path.
- [ ] Document the target operator flow: URL research -> store profile -> category selection -> full product collection -> data-derived filters -> exact product selection -> Excel/report export.

## Task 2: Remove Category-First Launcher Defaults

**Files:**
- Modify: `launcher/desktop_controller.py`
- Modify: `launcher/desktop_controller_helpers.py`
- Modify: `launcher/desktop_launcher.py`
- Test: `tests/test_desktop_launcher_controller.py`
- Test: `tests/test_desktop_launcher.py`

- [ ] Change launcher category sourcing so the UI prefers discovered categories and otherwise shows no category list instead of KB/default categories.
- [ ] Remove automatic selection of the first category in the launcher shell.
- [ ] Keep backend/category fallback logic available only where report/export runtime truly needs it, not in the first launcher screen.
- [ ] Keep Pyaterochka export actions wired through `utils.launcher_task_controller` -> `utils.local_task_registry` -> store export backend; do not call a new direct browser/parser path from launcher code.
- [ ] Add regression tests proving that:
  - before research, category list is empty;
  - after research, discovered categories appear;
  - launcher does not auto-select categories.

## Task 3: Rename Onboarding To Research In The UI Contract

**Files:**
- Modify: `launcher/desktop_window_sections.py`
- Modify: `launcher/desktop_view_helpers.py`
- Modify: `launcher/desktop_user_messages.py`
- Test: `tests/test_desktop_launcher.py`
- Test: `tests/test_desktop_view_helpers.py`

- [ ] Rename the visible launcher action from `Онбординг` to `Исследование`.
- [ ] Rename user-facing research messages accordingly.
- [ ] Keep internal task name `site_onboarding_discovery` unchanged for now to avoid breaking task contracts.
- [ ] Add regression tests for visible Russian labels and research-specific summary text.

## Task 4: Make Launcher Actions Stage-Aware

**Files:**
- Modify: `launcher/desktop_action_state.py`
- Modify: `launcher/desktop_controller.py`
- Modify: `launcher/desktop_view_helpers.py`
- Test: `tests/test_desktop_launcher_controller.py`
- Test: `tests/test_desktop_view_helpers.py`

- [ ] Define explicit launcher stages through state-derived rules:
  - no research result yet;
  - research complete;
  - export collected;
  - report built.
- [ ] Ensure:
  - research is always allowed;
  - export/report/filter actions require explicit selected categories;
  - result summary explains which stage the user is in.
- [ ] Add regression tests for stage-driven enabled/disabled behavior and summary text.

## Task 5: Make Post-Research Flow Honest

**Files:**
- Modify: `launcher/desktop_controller.py`
- Modify: `launcher/desktop_export_facets.py`
- Modify: `launcher/desktop_view_helpers.py`
- Test: `tests/test_desktop_launcher_controller.py`
- Test: `tests/test_desktop_view_helpers.py`

- [ ] After export, refresh filter counts from fresh export JSON and/or storage.
- [ ] Before export, explain that narrow filters are not available yet from real data.
- [ ] Make result summary clearly distinguish:
  - store research result;
  - collected export result;
  - filtered report result.
- [ ] Preserve full product attributes where available, including producer/manufacturer/supplier/vendor/brand, production country or region, category/subcategory, price, stock state, fish variants, wine color/style/sugar/alcohol attributes, product URL, image URL and raw store-specific fields.

## Task 5A: Add Exact Product Selection Before Report Export

**Files:**
- Modify: `models/launcher_state.py`
- Modify: `launcher/desktop_controller.py`
- Modify: `launcher/desktop_result_table.py`
- Modify: `launcher/desktop_result_table_widget.py`
- Modify: `utils/launcher_task_controller.py`
- Test: `tests/test_launcher_state.py`
- Test: `tests/test_desktop_launcher_controller.py`
- Test: `tests/test_desktop_result_table.py`

- [ ] Add launcher state for explicitly selected product IDs from the collected product workspace.
- [ ] Make the result table support selecting individual products after filters are applied.
- [ ] Ensure report export uses the explicit selected product set when present.
- [ ] Add regression tests proving that final Excel/report export can be scoped to selected products rather than all collected products.

## Task 6: Verification

**Files:**
- Test: `tests/test_desktop_launcher.py`
- Test: `tests/test_desktop_launcher_controller.py`
- Test: `tests/test_desktop_view_helpers.py`

- [ ] Run targeted launcher tests.
- [ ] Run full `pytest`.
- [ ] Run `compileall`.
- [ ] Run `scripts/architecture_check.py`.
- [ ] Relaunch `ParserRIba Launcher.lnk` and smoke the real window.
