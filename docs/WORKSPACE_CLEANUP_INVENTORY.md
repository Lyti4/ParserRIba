# Workspace Cleanup Inventory

Date: 2026-06-11

## Evidence

- `graphify update . --no-cluster` completed locally without API.
- `git ls-files archive` listed 36 tracked archive/history files.
- `rg` found no active runtime imports from `archive.*`.
- `scripts/architecture_check.py` already blocks active runtime imports from
  `archive.*`.
- Focused rename tests passed:
  `tests/test_interception_diagnostics_snapshot.py` and
  `tests/test_discover_pyaterochka_api.py`.

## Decisions

| Candidate | Decision | Evidence | Action |
| --- | --- | --- | --- |
| `archive/legacy_code/` | remove | No active runtime importers; architecture guard blocks future `archive.*` imports. | Delete tracked files; git history remains the archive. |
| `archive/project_history/` | remove | Human reference only; active docs must carry current decisions. | Delete tracked files; preserve any needed guidance in active docs. |
| `docs/LEGACY_MIGRATION_BACKLOG.md` | remove | Historical migration tracker; active architecture rules now live in current docs and checks. | Delete after active docs stop requiring it. |
| `docs/PROJECT_REVISION_2026-05-31.md` | remove | Historical audit snapshot; current state is in `PROJECT_STATE`, `NEXT_STEPS`, graphify and this inventory. | Delete after active docs stop requiring it. |
| `utils/interception_archive.py` | rename | Active diagnostic support imported by `scripts/discover_pyaterochka_api.py`. | Renamed to `utils/interception_diagnostics_snapshot.py`. |
| `tests/test_interception_archive.py` | rename | Active tests for diagnostic snapshot writer. | Renamed to `tests/test_interception_diagnostics_snapshot.py`. |
| `.venv/`, `.build-venv/` | keep-runtime-local | Local development environments; ignored by git. | Do not delete automatically. |
| `data/`, `profiles/`, `logs/` | keep-runtime-local | Local-first runtime state, reports, profiles, diagnostics. | Do not delete without explicit backup/user action. |
| `build/`, `dist/`, `graphify-out/`, `.serena/cache/` | keep-generated-local | Generated dev/build artifacts; ignored by git. | Can be cleaned locally only when not needed for current work. |
| `GeoLite2*.mmdb` | keep-runtime-local | Local GeoIP runtime support; ignored by git. | Do not delete without explicit user action. |

## Compatibility Notes

- Removing tracked archive files does not remove saved-manifest compatibility
  keys such as old Pyaterochka task names, `wine_styles` or `wine_breakdown`.
- Compatibility keys must be removed only through a separate migration decision.
- Git history is the long-term location for removed historical files.

## Verification Checklist

- `git ls-files archive` returns no files after removal.
- Active docs no longer instruct new agents to read removed archive/history docs.
- `rg "from archive|import archive"` in active Python surfaces finds only
  negative guard tests.
- `scripts/architecture_check.py` passes.
- Full validation gate passes before final cleanup commit.
