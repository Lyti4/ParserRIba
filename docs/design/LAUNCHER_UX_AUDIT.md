# ParserRIba Launcher UX Audit

Date: 2026-06-08

Source feature: `specs/007-launcher-ux-overhaul/`

## Baseline

- `scripts/run_desktop_launcher.py --smoke`: passed on 2026-06-08.
- Focused launcher tests passed on 2026-06-08:
  `test_desktop_workspace_shell`, `test_desktop_navigation`,
  `test_desktop_theme`, `test_desktop_result_table`,
  `test_desktop_filter_panel`, `test_desktop_filter_panel_found_browser`.
- Screenshot input shows a successful Pyaterochka product workspace with 36
  products, but the working area is visually overloaded.

## Current Pain Points

- The products screen has too many competing regions: filters, mini-catalog,
  found filters, product table, product card, profile/session panel and right
  inspector.
- Product table columns are too narrow for repeated product review.
- The no-selected-product card uses a large empty area instead of useful
  workspace context.
- Success state and older error journal lines can be visible together, reducing
  trust in current status.
- Future navigation sections are visible, but planned/disabled state needs to
  be explicit and testable.
- Diagnostics are present, but not yet a first-class support workspace with
  masked copy actions.

## Module Ownership

- Shell composition: `launcher/desktop_workspace_shell.py`
- Navigation rail: `launcher/desktop_navigation.py`
- Command/status strip: `launcher/desktop_command_strip.py`
- Right inspector: `launcher/desktop_inspector_panel.py`
- Workflow stack: `launcher/desktop_workflow_tabs.py`
- Products table: `launcher/desktop_result_table.py`,
  `launcher/desktop_result_table_widget.py`
- Product filters: `launcher/desktop_filter_panel.py`,
  `launcher/desktop_filter_slots.py`, `launcher/desktop_filter_summary.py`
- Product details: `launcher/desktop_product_details.py`
- Profile/session context: `launcher/desktop_profile_session_panel.py`
- Theme tokens: `launcher/desktop_theme.py`

## Graph/Flow Risks

- `desktop_workspace_shell.py` still wraps `desktop_workflow_tabs.py`; V4 shell
  is not yet a full replacement for the old tab stack.
- `desktop_launcher.py` still imports many UI modules directly, so ownership can
  blur if new UX work is added there.
- Status-adjacent text is spread across command strip, error panel, inspector,
  profile/session, report, result table and workflow tabs.
- Diagnostics, profile/session and report surfaces are cross-coupled enough
  that new text can easily duplicate or stale current state.

## Target Decisions

1. Product workspace gets the primary space in the first implementation slice.
2. Command strip owns compact user-facing current-state summary: outcome,
   progress, product count, filtered count, selected count, latest artifact
   and next action. Internal task names, raw profile IDs and raw phases stay in
   diagnostics/support artifacts.
3. Inspector sections are route-specific: product context on `Товары`,
   store/save context where useful, latest task where it does not duplicate the
   active workspace, and quick actions.
4. Planned modules remain visible but must not behave like ready dead-end pages.
5. Navigation states are explicit and testable: active, idle, completed,
   warning, disabled and planned.
6. Profile/session data remains in the inspector until a real profile
   workspace exists; the profile navigation item is disabled instead of acting
   like an empty page.
7. Diagnostics becomes a separate workspace before adding more support surface.

## First Implementation Slice

- Keep existing controller/task/storage contracts.
- Refine route availability and command strip formatting.
- Rebalance products workspace only after focused tests describe the desired
  table/filter/detail behavior.
- Run launcher smoke after each visible UI slice.

## Visual Review 2026-06-13

- Generated local screenshots:
  `logs/launcher_visual_review/launcher_light_1440x900.png` and
  `logs/launcher_visual_review/launcher_dark_1440x900.png`.
- Light and dark themes render the three-zone shell without overlapping main
  regions at 1440 x 900.
- Navigation planned/disabled items are visually distinct and not clickable.
- Diagnostics has a stable object name and copy actions for masked support
  text.
- Follow-up polish on 2026-06-13 made the research workspace summary and
  journal compact and moved scrollbars into centralized theme QSS, so the
  1440 x 900 dark screenshot no longer shows the bright native scrollbar.
- Follow-up inspector polish on 2026-06-13 renamed the right panel to
  `Сводка`, replaced technical `Профиль и сессия` wording with
  `Магазин и сохранения`, hid profile/version identifiers from saved-session
  labels, removed the duplicate profile/task summary blocks in successful
  states and kept diagnostics as the place for error detail.
- Remaining UX debt: the 960 x 760 review still needs a broader responsive
  layout slice because the research workspace can require horizontal scrolling
  and some forms become cramped next to the fixed inspector.

## Launcher IA And Theme Baseline 2026-06-13

Source feature: `specs/012-launcher-information-architecture/`

- Generated baseline screenshots for the new information-architecture track:
  `logs/launcher_visual_review/012-baseline-960x760/`,
  `logs/launcher_visual_review/012-baseline-1280x760/` and
  `logs/launcher_visual_review/012-baseline-1440x900/`.
- At 960 x 760, the top status still exposes technical task/phase fields and
  wraps into several lines before the workspace content starts.
- The right `Сводка` panel is fixed for the workspace while the main route area
  can require horizontal scrolling. This confirms that product/workspace
  readability cannot be solved by color changes alone.
- The current dark palette is readable but still visually heavy: most surfaces
  are close green/black variants, while the accent and scrollbar pull attention
  more than the active workflow.
- Phase 1 evidence confirms the next slice should start with a user-facing top
  status and route-specific right context, then update light/dark theme tokens.

## Launcher IA And Theme Closeout 2026-06-13

Source feature: `specs/012-launcher-information-architecture/`

- The top command strip now presents a short user-facing Russian state instead
  of raw profile IDs, internal task names and internal phases.
- The right inspector is route-specific. The global store/save summary is
  hidden or replaced where it duplicates the active workspace.
- The `Товары` route owns selected-product details in the route context, so the
  product table remains the primary workspace surface.
- The no-selection product context gives plain user guidance instead of showing
  internal profile/session identifiers.
- Light and dark themes now use modern neutral semantic tokens for surfaces,
  text, accent, selected rows, warnings, disabled/planned route states and
  scrollbars. The old green/beige palette remains only as archived
  compatibility data in code.
- Remaining UX debt: the 960 x 760 launcher still needs a separate responsive
  layout slice for cramped forms and horizontal workspace scrolling.
