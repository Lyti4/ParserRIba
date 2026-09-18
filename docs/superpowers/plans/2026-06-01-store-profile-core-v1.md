# Store Profile Core V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `StoreProfile` the central local owner for per-site catalog, product workspace, filters, reports, artifacts and future price history.

**Architecture:** Add a SQLite-backed profile repository that accepts the existing Launcher V3 snapshot contract first, then gradually moves launcher loading/saving from JSON-only snapshots into profile versions. The launcher keeps working through current state models while the storage layer becomes the single source of saved sessions.

**Tech Stack:** Python 3.11, SQLite, Pydantic v2 state models, PySide6 launcher, pytest.

---

## File Structure

- `utils/store_profile_repository.py`: new central SQLite repository for profiles, versions, catalog snapshots, product workspaces, presets and price observations.
- `tests/test_store_profile_repository.py`: unit tests for schema creation, saving launcher snapshots, loading latest session and recording price observations.
- `launcher/desktop_controller_profile.py`: later bridge from launcher task completion into `StoreProfileRepository`.
- `launcher/desktop_profile_session_panel.py`: later source for profile/session UI data loaded from SQLite.
- `docs/PROJECT_STATE.md`, `docs/NEXT_STEPS.md`, `docs/PROJECT_STRUCTURE.md`: document the new central profile layer after the first code slice passes.

## Task 1: SQLite StoreProfile Repository

**Files:**
- Create: `utils/store_profile_repository.py`
- Create: `tests/test_store_profile_repository.py`

- [x] **Step 1: Write tests for central profile schema**

Expected behavior:

```python
repository = StoreProfileRepository(tmp_path / "profiles.db")
repository.initialize()
assert "store_profiles" in sqlite_master_tables
assert "profile_versions" in sqlite_master_tables
assert "catalog_snapshots" in sqlite_master_tables
assert "product_workspace_snapshots" in sqlite_master_tables
assert "filter_presets" in sqlite_master_tables
assert "report_presets" in sqlite_master_tables
assert "price_observations" in sqlite_master_tables
```

- [x] **Step 2: Implement schema initialization**

Create all v1 tables with JSON text columns for current snapshot payloads. Keep the schema migration-friendly: stable IDs, timestamps, indexes by profile/site/version.

- [x] **Step 3: Write tests for saving a Launcher V3 snapshot**

Build `LauncherAppState` with profile, catalog, products, filters and report columns. Save it through `repository.save_launcher_state(...)`. Assert:

```python
latest = repository.get_latest_profile_by_site("pyaterochka", "https://5ka.ru")
assert latest["profile"]["profile_id"] == "profile-1"
assert latest["catalog"]["selected_node_urls"] == ["https://5ka.ru/catalog/fish/"]
assert latest["products"]["products_count"] == 2
assert latest["report"]["selected_columns"] == ["Товар", "Цена", "Ссылка"]
```

- [x] **Step 4: Implement save/load latest snapshot**

Reuse `utils.launcher_profile_snapshot.build_launcher_profile_snapshot` as the first payload contract. Do not duplicate product parsing rules in the repository.

- [x] **Step 5: Write tests for price observations**

Save two price observations for one product/profile and assert ordered history and snapshot comparison inputs are available.

- [x] **Step 6: Implement price observation insert/list**

Use `profile_id`, `product_id`, `product_url`, `category`, `price`, `old_price`, `in_stock`, `captured_at`, `session_id`.

- [x] **Step 7: Verify**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_store_profile_repository.py
.\.venv\Scripts\python.exe -m compileall -q utils tests
```

## Task 2: Persist StoreProfile After Launcher Tasks

**Files:**
- Modify: `launcher/desktop_controller_profile.py`
- Modify: `launcher/desktop_controller.py`
- Test: `tests/test_desktop_launcher_controller_tasks.py`

- [x] Save the existing JSON snapshot as before.
- [x] Also write the same state into `StoreProfileRepository` at `data/profiles/store_profiles.db`.
- [x] Add the SQLite path to `state.profile.diagnostics["store_profile_db_path"]`.
- [x] Keep JSON snapshot as a human-readable compatibility artifact.

## Task 3: Load Latest Profile Session Without Browser

**Files:**
- Modify: `launcher/desktop_controller.py`
- Modify: `launcher/desktop_profile_session_panel.py`
- Test: `tests/test_desktop_launcher_controller_profile_load.py`

- [x] Add controller method `load_latest_profile_session(shop, site_url)`.
- [x] Populate `state.profile`, `state.catalog`, `state.products`, `state.dynamic_filters`, `state.filters`, `state.report`, `state.selection` from latest SQLite snapshot.
- [x] Do not start Camoufox or local task subprocess.
- [x] Show a Russian status message: `Загружена последняя сохранённая сессия профиля.`

## Task 4: Launcher Profile UI

**Files:**
- Modify: `launcher/desktop_profile_session_panel.py`
- Modify: `launcher/desktop_window_sections.py`
- Test: `tests/test_desktop_profile_session_panel.py`

- [x] Add `Открыть последнюю сессию` in the existing `Профиль и сессия` pane.
- [x] Add `Сохранить профиль`.
- [x] Keep controls compact; do not add a new top-level tab yet.
- [x] The current panel remains read-only when no profile exists.

## Task 5: Presets

**Files:**
- Modify: `utils/store_profile_repository.py`
- Modify: `launcher/desktop_controller_profile.py`
- Test: `tests/test_store_profile_repository.py`

- [x] Save selected filter preset from `state.filters`.
- [x] Save selected report columns from `state.report.selected_columns`.
- [x] Load presets with profile latest session.

## Task 6: Price History Report Slice

**Files:**
- Modify: `utils/store_profile_repository.py`
- Modify: `launcher/desktop_report_panel.py`
- Test: `tests/test_store_profile_repository.py`

- [x] Store price observations whenever product workspace is saved.
- [x] Add repository method to compare two latest sessions for one profile.
- [x] Keep the comparison data in storage/report core; do not add a separate dashboard.

## Self-Review

- Covers one-site-one-profile, profile versions, catalog snapshots, product workspace snapshots, presets and price history.
- Does not add Postgres, backend, cloud services or paid APIs.
- Keeps existing JSON snapshots during migration.
- Keeps unknown sites as `discovery_only` until a product adapter exists.
- First task is independently testable and does not require launcher UI changes.
