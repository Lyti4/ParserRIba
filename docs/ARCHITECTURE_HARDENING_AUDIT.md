# ParserRIba Architecture Hardening Audit

Date: 2026-06-07

Source feature: `specs/004-architecture-hardening-code-quality/`

Graphify baseline:

- `graphify update . --force` completed on 2026-06-07.
- `graphify-out/GRAPH_REPORT.md` built from commit `ba87ab42` before the final hardening commit.
- Graph size: 6674 nodes, 15239 edges, 275 communities.
- Graphify is evidence for prioritization. Current source reads and tests remain required before code changes.

Validation baseline:

- `scripts/architecture_check.py` passes.
- Known pre-existing warning: `tests/test_desktop_filter_panel.py` has 478 lines; target for tests is <= 450.
- Added guardrails in this feature: active runtime imports from `archive.*`, direct store-specific imports from shared roots, runtime `print()`, `time.sleep()`, `close()` review warnings, generated/runtime artifact scan exclusions and file-size reporting.

## Finding Format

Each finding uses:

- id;
- layer;
- file path;
- risk type;
- severity;
- evidence;
- user or maintenance impact;
- remediation;
- status.

## Findings

### ARCH-001 - Runtime imports from archived legacy code

- Layer: Launcher/Task runtime
- File path: active runtime under `launcher/`, `utils/`, `stores/`, `models/`
- Risk type: legacy dependency
- Severity: blocking
- Evidence: current checker did not explicitly block `archive.*` imports before this feature.
- Impact: active product runtime could depend on archived reference code and make replacement discipline unclear.
- Remediation: add architecture check coverage for active runtime imports from `archive.*`.
- Status: fixed in this slice by `runtime-imports-archive` check and test.

### ARCH-002 - Graph hubs need targeted maintainability review

- Layer: Launcher/Storage/Product model
- File path: `models/launcher_state.py`, `utils/store_profile_repository.py`, `launcher/desktop_controller.py`
- Risk type: maintainability hotspot
- Severity: warning
- Evidence: graphify hub list names `LauncherAppState`, `StoreProfileRepository` and `DesktopLauncherController` among top connected nodes.
- Impact: future profiles, favorites, sessions and reports can become harder to change safely if these hubs keep growing.
- Remediation: choose one behavior-preserving cleanup slice after boundary guardrails are in place.
- Status: first cleanup completed for launcher filter alias compatibility via `launcher/desktop_filter_aliases.py`; larger graph hubs remain future review targets.

### ARCH-003 - Store-specific compatibility remains in shared roots

- Layer: Task/Launcher shared roots
- File path: `utils/launcher_task_controller.py`, `utils/store_catalog_registry.py`, launcher state/display helpers
- Risk type: store-specific compatibility debt
- Severity: compatibility debt
- Evidence: current `rg` finds Pyaterochka, `fish_catalog`, `wine_styles` and `wine_breakdown` references in shared modules.
- Impact: these references can become accidental defaults if not classified.
- Remediation: classify each reference as adapter-owned, compatibility alias, saved-manifest compatibility, fixture/test or remediation-needed.
- Status: classified baseline below. Direct Pyaterochka imports from shared roots are now blocked except for adapter/registry-owned paths. Launcher `wine_styles` aliasing is centralized in `launcher/desktop_filter_aliases.py`.

### ARCH-004 - Runtime status outcomes must not collapse into false success

- Layer: Launcher/Task runtime
- File path: `launcher/desktop_controller_task_state.py`, `launcher/desktop_controller.py`, `utils/store_export_runtime.py`
- Risk type: status mismatch
- Severity: blocking
- Evidence: empty product export previously risked being shown like a successful task.
- Impact: non-technical users could believe data was collected when product workspace is empty.
- Remediation: route manifest status through explicit launcher status mapping and preserve precise empty/blocked reasons.
- Status: fixed by explicit `launcher_task_status_from_manifest()` and backend reason tests.

## Compatibility Exceptions

### COMPAT-001 - Store registry owns Pyaterochka binding

- Path: `utils/store_catalog_registry.py`
- Keys: `pyaterochka`, `5ka.ru`, `fish_catalog`
- Owner layer: Store adapter registry
- Reason: This module is the store binding layer for known-site resolution, backend selection and host matching.
- Removal condition: only if the registry is replaced by a different explicit adapter registry contract.
- Status: accepted exception.

### COMPAT-002 - Launcher task compatibility wrappers

- Path: `utils/launcher_task_controller.py`
- Keys/functions: Pyaterochka launcher helper wrappers, `fish_catalog`, `wine_catalog`
- Owner layer: Task compatibility facade
- Reason: Existing callers/tests can still use old launcher-facing aliases while active routing uses generic store/report task paths.
- Removal condition: all active callers use generic helper names and saved compatibility entrypoints have a migration/removal decision.
- Status: compatibility debt.

### COMPAT-003 - Launcher UI labels for old task/field names

- Path: `launcher/desktop_ui_text.py`
- Keys: old Pyaterochka task names, `fish_catalog`, `wine_styles`
- Owner layer: Launcher display compatibility
- Reason: Old manifests and compatibility task names still need readable labels.
- Removal condition: old task labels and legacy filter keys are no longer loaded from saved data.
- Status: compatibility debt.

### COMPAT-004 - `wine_styles` as saved-manifest alias for subcategories

- Paths: `launcher/desktop_filter_aliases.py`, `launcher/desktop_controller_helpers.py`, `launcher/desktop_export_facets.py`, `launcher/desktop_state_readers.py`
- Key: `wine_styles`
- Owner layer: Launcher saved-data compatibility
- Reason: Saved reports/manifests can still contain `wine_styles`; active user meaning is `subcategories`.
- Removal condition: saved data migration removes old key.
- Status: centralized compatibility helper exists; legacy key remains intentionally published for saved profile/report compatibility.

### COMPAT-005 - `wine_breakdown` not active in inspected shared roots

- Path: none found in inspected shared-root files
- Key: `wine_breakdown`
- Owner layer: Report manifest compatibility if present elsewhere
- Reason: Feature planning mentioned this key, but current inspected files did not contain it.
- Removal condition: classify only if future `rg` finds active shared-root usage.
- Status: no active exception in inspected files.
