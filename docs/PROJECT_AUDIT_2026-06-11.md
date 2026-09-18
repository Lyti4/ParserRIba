# ParserRIba Project Audit

Date: 2026-06-11

## Scope

This audit combines the existing `graphify-out` snapshot, current project docs,
git inventory, architecture checks, encoding checks and focused static scans.

Graphify status:

- Existing graph: `graphify-out/GRAPH_REPORT.md`
- Previous graph commit: `ba87ab42`
- Current HEAD during audit: `6eb14dd`
- Local code graph refresh command: `graphify update . --no-cluster`
- Refreshed code graph: 7325 nodes, 33583 raw edges
- Refreshed report after local clustering: 7297 nodes, 16219 edges,
  332 communities
- Token cost: 0 input, 0 output
- No external API key was added. Semantic doc/image extraction and LLM community
  labels still require an explicit backend/API decision, but code graph refresh
  works locally without API.

## Current Health

- Git working tree was clean before this audit report.
- `scripts/encoding_guard.py --all` passed.
- Encoding baseline: 0 files, 0 findings.
- Compatibility encoding markers: 11 intentional markers in 3 files:
  `utils/site_filter_descriptors.py`, `utils/product_display_fields.py`,
  `utils/product_report_display_fields.py`.
- `scripts/architecture_check.py` passed with one known warning:
  `launcher/desktop_launcher.py` has 310 lines.
- `scripts/agent_ops_check.py --scope all` passed.
- Focused guard tests passed:
  `tests/test_architecture_check.py`, `tests/test_encoding_guard.py`,
  `tests/test_agent_ops_check.py`.
- No tracked `.env`, `data/`, `logs/`, `profiles/`, `build/`, `dist/`,
  `GeoLite2-City.mmdb` or `__pycache__` files were found.

## Main Findings

### AUDIT-001 - Graphify Code Graph Works Locally Without API

The first attempted command used the wrong shape for this installed CLI. The
correct local command is `graphify update . --no-cluster`, which re-extracts
code without an LLM key. The refreshed graph is current for code structure, but
semantic extraction of docs and generated community labels remain limited
without an explicit backend/API decision.

Recommendation:

- Use `graphify update . --no-cluster` after code-heavy slices.
- Use `graphify cluster-only . --no-viz --no-label` when community labels can
  stay generic.
- Do not add external LLM/API keys automatically.

### AUDIT-002 - Launcher UX Is The Biggest Product Risk

Specs and current project docs agree that the launcher is the main user entry.
The active UX pain is not missing backend capability but a cramped workbench:
duplicated status text, dense panels, narrow product table, unclear diagnostics
and future sections that can look active before they are useful.

Recommendation:

- Make `specs/007-launcher-ux-overhaul/` the next product-facing feature.
- Start with the products workspace: table priority, compact filter summary,
  useful empty product card, clearer selected/report state.
- Preserve existing controller/task/storage contracts while migrating UI slices.

### AUDIT-003 - Workspace Cleanup Was A Real Debt

Tracked `archive/` contained 36 files before cleanup. Architecture guardrails
blocked active runtime imports from archive, so removal was mainly a workspace
clarity and future-agent-context issue.

Recommendation:

- Execute `specs/006-workspace-cleanup/` in slices:
  inventory/doc update first, then tracked history removal, then active
  archive-like module rename if needed.
- Do not delete local runtime folders such as `data/`, `profiles/`, `logs/` or
  `.venv` without explicit backup/user approval.

### AUDIT-004 - Store-Neutral Unification Is Improved But Not Finished

Pyaterochka-specific imports are mostly in adapter-owned paths and explicit
registry/compatibility boundaries. Remaining `fish`, `wine`, `wine_styles` and
`wine_breakdown` references are mostly compatibility or intent-specific logic,
but they remain easy to misuse in future code.

Recommendation:

- Keep narrowing compatibility keys only when saved-data migration is clear.
- Keep active UI labels neutral: product subcategory/subtype, not wine-specific
  language outside wine intent.
- Keep Pyaterochka behavior behind store adapter and knowledge base.

### AUDIT-005 - Encoding Work Is Now A Strength

The encoding baseline is zero, guard coverage includes BOM, replacement char,
classic mojibake, C1-control mojibake and CP1252/box-drawing chains. This
directly reduces future token waste and broken Russian UI/docs.

Recommendation:

- Keep `encoding_guard.py --changed` after docs/UI/tests edits.
- Use `utf8_command.py` when PowerShell output is suspicious.
- Do not reintroduce raw mojibake examples in docs; use ASCII-safe
  `unicode_escape` literals.

### AUDIT-006 - File Size Pressure Is Manageable

Largest files are mostly tests and orchestration entrypoints. Current warning is
`launcher/desktop_launcher.py` at 310 lines. Several active modules sit near the
300-line target, so broad UX work can easily push them over budget.

Recommendation:

- Before launcher UX implementation, define view/component boundaries.
- Extract new UI slices into focused modules instead of growing
  `desktop_launcher.py` and `desktop_controller.py`.
- Keep large tests under one responsibility; split only with safe-file-split
  workflow.

## Recommended Next Order

1. Update stale docs/spec notes that still describe old encoding baseline debt.
2. Execute `specs/007-launcher-ux-overhaul/` product workspace slice.
3. Execute `specs/006-workspace-cleanup/` inventory/docs slice, then remove
   tracked history only after validation.
4. Refresh graphify after docs/code stabilization.
5. Continue store-neutral cleanup only where compatibility migration is clear.

## Commands Used

```powershell
git status --short
git rev-parse HEAD
graphify update . --no-cluster
graphify cluster-only . --no-viz --no-label
graphify diagnose multigraph --json
graphify query "Audit ParserRIba architecture risks..." --budget 2000
graphify query "Trace launcher product collection data flow..." --budget 2000
graphify query "Find remaining store-specific or legacy coupling..." --budget 2000
.\.venv\Scripts\python.exe scripts\encoding_guard.py --all
.\.venv\Scripts\python.exe scripts\encoding_guard.py --baseline-report
.\.venv\Scripts\python.exe scripts\encoding_guard.py --compatibility-report
.\.venv\Scripts\python.exe scripts\architecture_check.py
.\.venv\Scripts\python.exe scripts\agent_ops_check.py --scope all
.\.venv\Scripts\python.exe -m pytest -q tests\test_architecture_check.py tests\test_encoding_guard.py tests\test_agent_ops_check.py
git ls-files .env data logs profiles build dist GeoLite2-City.mmdb __pycache__ archive
git ls-files archive
```
