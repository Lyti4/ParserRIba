# Catalog Tree Discovery Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first production slice of the launcher action `Исследование`: adaptive catalog tree discovery, site profile persistence with history, and launcher integration with phased progress and streamed categories.

**Architecture:** Build discovery as a dedicated core with explicit domain models, repository interfaces, adaptive browser collection, validation, and launcher-safe view models. Keep the current Pyaterochka runtime only as a legacy reference and diagnostics path; the new discovery core must not be blocked on reusing or embedding that runtime. Persist profiles in SQLite plus JSON snapshots so the domain stays storage-agnostic for a future stronger database.

**Tech Stack:** Python 3.11, asyncio, Camoufox async API, Pydantic v2, SQLite, openpyxl, PySide6, pytest.

---

## File Map

- `models/catalog_discovery.py`
  - extend from flat evidence lists to tree/discovery graph domain models.
- `models/onboarding.py`
  - update launcher-facing onboarding result contract to reference the current site profile and phased research state.
- `models/launcher_state.py`
  - hold research mode, current phase, streamed categories, and current active profile summary.
- `utils/catalog_discovery.py`
  - keep generic HTML signal extraction, but make it a low-level source provider instead of the final decision maker.
- `utils/browser_catalog_discovery.py`
  - provide adaptive browser collection for the new discovery core and keep any legacy Pyaterochka-specific flow isolated as reference-only code.
- `utils/site_onboarding.py`
  - stop assembling category trees ad hoc; call the new discovery core and build launcher-facing results from it.
- `utils/onboarding_storage.py`
  - keep onboarding sessions, add profile metadata persistence only if shared tables remain coherent.
- `utils/product_storage.py`
  - initialize profile tables or delegate to a separate profile repository initializer while keeping current product history intact.
- `utils/report_filter_facets.py`
  - no deep rework in this plan; only keep compatibility with selected categories and profile-driven launcher flow if needed.
- `utils/discovery_profile_repository.py`
  - new repository interface and SQLite implementation for site profiles and profile history.
- `utils/discovery_profile_snapshot.py`
  - new JSON snapshot writer for manual debugging and profile inspection.
- `utils/catalog_tree_discovery/`
  - new focused package for the discovery core:
  - `runner.py`
  - `surface_collectors.py`
  - `graph_builder.py`
  - `tree_normalizer.py`
  - `listing_validator.py`
  - `phase_events.py`
- `launcher/desktop_controller.py`
  - trigger research runs, receive phase updates, and keep only simple Russian summaries in UI state.
- `launcher/desktop_view_helpers.py`
  - render Russian research statuses and current-category streaming.
- `launcher/desktop_window_sections.py`
  - add research mode toggle and phase/progress widgets if not already present.
- `launcher/desktop_ui_text.py`
  - centralize Russian labels for phases, modes, warnings, and “Дополнительно найденные фильтры”.
- `tests/test_browser_catalog_discovery.py`
  - adapt browser discovery tests to the new result contract.
- `tests/test_site_onboarding.py`
  - verify onboarding now builds results from site profiles instead of direct category lists.
- `tests/test_onboarding_registries.py`
  - verify known-store routing still works.
- `tests/test_launcher_state.py`
  - verify new research-phase state and mode toggles.
- `tests/test_desktop_launcher_controller.py`
  - verify live/quiet research mode behavior and streamed categories.
- `tests/test_desktop_view_helpers.py`
  - verify Russian launcher text for research phases and warnings.
- `tests/test_product_storage.py`
  - verify profile tables do not break current product/price history behavior.
- `tests/test_catalog_tree_discovery_runner.py`
  - new tests for adaptive discovery orchestration.
- `tests/test_discovery_profile_repository.py`
  - new tests for SQLite profile persistence and history.
- `tests/test_discovery_profile_snapshot.py`
  - new tests for JSON snapshot writing.

## Scope Split

This plan intentionally stops at the end of the `Исследование` slice plus launcher integration.

This plan does **not** implement:

- full product selection before report export;
- the full “Дополнительно найденные фильтры” derivation engine;
- store-specific strategy learning beyond storing the signals needed later.

Those belong in the next plan after `Исследование` is stable.

### Task 1: Freeze Discovery Domain Models

**Files:**
- Modify: `models/catalog_discovery.py`
- Modify: `models/onboarding.py`
- Modify: `models/launcher_state.py`
- Test: `tests/test_launcher_state.py`
- Test: `tests/test_site_onboarding.py`

- [ ] Define richer discovery models in `models/catalog_discovery.py`.

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DiscoverySource = Literal["dom", "network", "mixed", "manual_confirmed"]
ValidationState = Literal[
    "unknown",
    "listing_valid",
    "menu_only",
    "promo",
    "pdf_flipbook",
    "region_gate",
    "challenge",
    "blocked",
    "empty",
]


class RouteHint(BaseModel):
    kind: str
    value: str
    source: DiscoverySource = "dom"


class DiscoveryNode(BaseModel):
    node_id: str
    label_ru: str
    label_original: str = ""
    canonical_url: str = ""
    candidate_urls: list[str] = Field(default_factory=list)
    child_ids: list[str] = Field(default_factory=list)
    parent_ids: list[str] = Field(default_factory=list)
    source: DiscoverySource = "dom"
    validation_state: ValidationState = "unknown"
    listing_confidence: float = 0.0
    route_hints: list[RouteHint] = Field(default_factory=list)
    protection_signals: list[str] = Field(default_factory=list)
    manual_step_seen: bool = False
    last_seen_run_id: str = ""
```

- [ ] Add site-profile oriented models in `models/catalog_discovery.py`.

```python
class SiteProfileVersion(BaseModel):
    profile_id: str
    version_id: str
    shop_slug: str
    site_url: str
    run_id: str
    primary_root_ids: list[str] = Field(default_factory=list)
    nodes: list[DiscoveryNode] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class DiscoveryPhaseEvent(BaseModel):
    phase: str
    status: str
    message_ru: str
    discovered_categories: list[str] = Field(default_factory=list)
```

- [ ] Extend `models/onboarding.py` to return the active profile and live research summary instead of only flat categories.

```python
class OnboardingResult(BaseModel):
    ...
    active_profile_id: str = ""
    active_profile_version_id: str = ""
    streamed_categories: list[str] = Field(default_factory=list)
    research_mode: str = "live"
    current_phase: str = ""
```

- [ ] Extend `models/launcher_state.py` with launcher research state.

```python
class LauncherResearchState(BaseModel):
    mode: Literal["live", "quiet"] = "live"
    current_phase: str = ""
    current_status: str = ""
    streamed_categories: list[str] = Field(default_factory=list)
    active_profile_id: str = ""
    active_profile_version_id: str = ""
```

- [ ] Run targeted tests and update them for the new contract.

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_launcher_state.py tests/test_site_onboarding.py -v`
Expected: failing tests that show missing fields or outdated result expectations.

- [ ] Commit the model-contract slice.

```bash
git add models/catalog_discovery.py models/onboarding.py models/launcher_state.py tests/test_launcher_state.py tests/test_site_onboarding.py
git commit -m "feat: add discovery profile domain models"
```

### Task 2: Add Storage-Agnostic Profile Persistence

**Files:**
- Create: `utils/discovery_profile_repository.py`
- Create: `utils/discovery_profile_snapshot.py`
- Modify: `utils/onboarding_storage.py`
- Modify: `utils/product_storage.py`
- Test: `tests/test_discovery_profile_repository.py`
- Test: `tests/test_discovery_profile_snapshot.py`
- Test: `tests/test_product_storage.py`

- [ ] Add repository protocol and SQLite repository implementation.

```python
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from models.catalog_discovery import SiteProfileVersion


class DiscoveryProfileRepository(Protocol):
    def initialize(self) -> None: ...
    def save_profile_version(self, profile: SiteProfileVersion) -> None: ...
    def get_latest_profile(self, shop_slug: str, site_url: str) -> SiteProfileVersion | None: ...
    def list_profile_versions(self, shop_slug: str, site_url: str) -> list[SiteProfileVersion]: ...
```

- [ ] Create SQLite tables for current profile and profile history.

```sql
CREATE TABLE IF NOT EXISTS discovery_profiles (
    profile_id TEXT PRIMARY KEY,
    shop_slug TEXT NOT NULL,
    site_url TEXT NOT NULL,
    latest_version_id TEXT NOT NULL,
    latest_payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS discovery_profile_versions (
    version_id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL,
    shop_slug TEXT NOT NULL,
    site_url TEXT NOT NULL,
    run_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

- [ ] Add JSON snapshot writer for manual inspection.

```python
class DiscoveryProfileSnapshotWriter:
    def __init__(self, base_dir: Path | str) -> None:
        self.base_dir = Path(base_dir)

    def write_snapshot(self, profile: SiteProfileVersion) -> Path:
        target_dir = self.base_dir / profile.shop_slug / "profiles"
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{profile.version_id}.json"
        path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
        return path
```

- [ ] Keep onboarding session storage separate from profile history, but allow `OnboardingStorage` to read the latest active profile id when needed.

- [ ] Verify storage tests fail before implementation.

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_discovery_profile_repository.py tests/test_discovery_profile_snapshot.py tests/test_product_storage.py -v`
Expected: FAIL because repository/snapshot modules do not exist yet.

- [ ] Implement the repository and tests until they pass.

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_discovery_profile_repository.py tests/test_discovery_profile_snapshot.py tests/test_product_storage.py -v`
Expected: PASS.

- [ ] Commit the persistence slice.

```bash
git add utils/discovery_profile_repository.py utils/discovery_profile_snapshot.py utils/onboarding_storage.py utils/product_storage.py tests/test_discovery_profile_repository.py tests/test_discovery_profile_snapshot.py tests/test_product_storage.py
git commit -m "feat: persist discovery profiles with history"
```

### Task 3: Extract The Catalog Tree Discovery Core

**Files:**
- Create: `utils/catalog_tree_discovery/__init__.py`
- Create: `utils/catalog_tree_discovery/surface_collectors.py`
- Create: `utils/catalog_tree_discovery/graph_builder.py`
- Create: `utils/catalog_tree_discovery/tree_normalizer.py`
- Create: `utils/catalog_tree_discovery/listing_validator.py`
- Create: `utils/catalog_tree_discovery/phase_events.py`
- Modify: `utils/catalog_discovery.py`
- Test: `tests/test_catalog_tree_discovery_runner.py`

- [ ] Move low-level signal collection into `surface_collectors.py`.

```python
class SurfaceSignals(BaseModel):
    dom_categories: list[CategoryEvidence] = Field(default_factory=list)
    dom_products: list[ProductLinkEvidence] = Field(default_factory=list)
    api_hints: list[ApiEvidence] = Field(default_factory=list)
    documents: list[DocumentEvidence] = Field(default_factory=list)
    raw_hrefs: list[str] = Field(default_factory=list)
```

- [ ] Make `utils/catalog_discovery.py` a generic signal helper, not the final tree assembler.

```python
def collect_catalog_surface_signals(*, site_url: str, final_url: str, status_code: int, html: str) -> SurfaceSignals:
    ...
```

- [ ] Add graph assembly in `graph_builder.py`.

```python
def build_discovery_graph(signals: SurfaceSignals) -> list[DiscoveryNode]:
    # Merge duplicate urls, normalize labels, and connect likely parent-child nodes.
    ...
```

- [ ] Add Russian label normalization in `tree_normalizer.py`.

```python
def normalize_label_for_launcher(original: str) -> str:
    # Strip noise, preserve readable Russian, and fall back safely when needed.
    ...
```

- [ ] Add short listing validation in `listing_validator.py`.

```python
class ValidationProbeResult(BaseModel):
    validation_state: ValidationState
    route_hints: list[RouteHint] = Field(default_factory=list)
    protection_signals: list[str] = Field(default_factory=list)
```

- [ ] Add phase-event helpers in `phase_events.py`.

```python
def make_phase_event(phase: str, status: str, message_ru: str, categories: list[str] | None = None) -> DiscoveryPhaseEvent:
    return DiscoveryPhaseEvent(...)
```

- [ ] Write failing tests for signal collection, graph assembly, normalization, and validation-state classification.

```python
def test_graph_builder_merges_duplicate_category_urls():
    ...

def test_normalize_label_for_launcher_prefers_clean_russian():
    ...

def test_listing_validator_classifies_pdf_surface():
    ...
```

- [ ] Run the focused tests.

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_catalog_tree_discovery_runner.py tests/test_browser_catalog_discovery.py -v`
Expected: FAIL until the new package is wired in.

- [ ] Implement until tests pass.

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_catalog_tree_discovery_runner.py tests/test_browser_catalog_discovery.py -v`
Expected: PASS.

- [ ] Commit the discovery-core extraction.

```bash
git add utils/catalog_discovery.py utils/catalog_tree_discovery tests/test_catalog_tree_discovery_runner.py tests/test_browser_catalog_discovery.py
git commit -m "feat: extract catalog tree discovery core"
```

### Task 4: Add Adaptive Browser Research Runner

**Files:**
- Create: `utils/catalog_tree_discovery/runner.py`
- Modify: `utils/browser_catalog_discovery.py`
- Modify: `utils/store_catalog_registry.py`
- Modify: `scripts/run_site_onboarding.py`
- Test: `tests/test_catalog_tree_discovery_runner.py`
- Test: `tests/test_onboarding_registries.py`

- [ ] Build an orchestrator that reuses the existing protected browser path and emits phase events.

```python
async def run_catalog_tree_discovery(
    site_url: str,
    *,
    shop: str | None = None,
    mode: str = "live",
    headless: bool | str | None = None,
    manual_wait: bool = False,
    listen_seconds: int = 6,
) -> SiteProfileVersion:
    ...
```

- [ ] For Pyaterochka, keep the current Camoufox/proxy/GeoIP/profile/human behavior startup path from `utils/browser_catalog_discovery.py`.

- [ ] Implement adaptive expansion rules:

```python
MAX_REPEAT_URLS = 3
MAX_EMPTY_BRANCHES = 5
MAX_DISCOVERY_DEPTH = 8
```

- [ ] Implement manual challenge behavior with partial persistence semantics.

```python
if challenge_detected and not solved_within_timeout:
    profile.notes.append("partial_research_due_to_challenge")
    return partial_profile
```

- [ ] Ensure `scripts/run_site_onboarding.py` can run and serialize the richer research result.

- [ ] Run tests for runner behavior and known-store routing.

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_catalog_tree_discovery_runner.py tests/test_onboarding_registries.py tests/test_site_onboarding.py -v`
Expected: PASS.

- [ ] Commit the runner slice.

```bash
git add utils/catalog_tree_discovery/runner.py utils/browser_catalog_discovery.py utils/store_catalog_registry.py scripts/run_site_onboarding.py tests/test_catalog_tree_discovery_runner.py tests/test_onboarding_registries.py tests/test_site_onboarding.py
git commit -m "feat: add adaptive browser research runner"
```

### Task 5: Rebuild Site Onboarding Around Profiles

**Files:**
- Modify: `utils/site_onboarding.py`
- Modify: `utils/onboarding_artifacts.py`
- Modify: `utils/launcher_task_controller.py`
- Modify: `utils/local_task_registry.py`
- Test: `tests/test_site_onboarding.py`
- Test: `tests/test_launcher_task_controller_onboarding.py`
- Test: `tests/test_local_task_runtime.py`

- [ ] Replace direct category-tree assembly in `utils/site_onboarding.py` with calls into the new runner + profile repository.

```python
profile = run_catalog_tree_discovery(...)
result = build_onboarding_result_from_profile(profile, ...)
```

- [ ] Keep `site_onboarding_discovery` as the public task name for compatibility.

- [ ] Ensure the launcher-facing task result returns:

```python
{
    "category_tree": ...,
    "catalog_discovery": ...,
    "selected_categories": ...,
    "active_profile_id": ...,
    "active_profile_version_id": ...,
    "streamed_categories": ...,
    "current_phase": ...,
}
```

- [ ] Keep artifact generation compatible with current `data/onboarding/...` layout, but add profile snapshot paths when available.

- [ ] Run onboarding and task-controller tests.

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_site_onboarding.py tests/test_launcher_task_controller_onboarding.py tests/test_local_task_runtime.py -v`
Expected: PASS.

- [ ] Commit the onboarding integration.

```bash
git add utils/site_onboarding.py utils/onboarding_artifacts.py utils/launcher_task_controller.py utils/local_task_registry.py tests/test_site_onboarding.py tests/test_launcher_task_controller_onboarding.py tests/test_local_task_runtime.py
git commit -m "feat: drive onboarding from discovery profiles"
```

### Task 6: Integrate Live Research Into Launcher

**Files:**
- Modify: `launcher/desktop_controller.py`
- Modify: `launcher/desktop_view_helpers.py`
- Modify: `launcher/desktop_window_sections.py`
- Modify: `launcher/desktop_ui_text.py`
- Modify: `launcher/desktop_launcher.py`
- Test: `tests/test_desktop_launcher_controller.py`
- Test: `tests/test_desktop_view_helpers.py`
- Test: `tests/test_desktop_launcher.py`

- [ ] Add research mode selection to launcher state and UI.

```python
RESEARCH_MODE_LABELS = {
    "live": "Пошаговое исследование",
    "quiet": "Только итоговый результат",
}
```

- [ ] Add Russian phase labels to `launcher/desktop_ui_text.py`.

```python
RESEARCH_PHASE_LABELS = {
    "open_site": "Открытие сайта",
    "collect_surface": "Поиск структуры каталога",
    "validate_nodes": "Проверка разделов",
    "collect_hints": "Сбор признаков и маршрутов",
    "persist_profile": "Сохранение профиля",
    "build_tree": "Подготовка дерева",
}
```

- [ ] Update the controller to:
  - launch research in live or quiet mode;
  - append streamed categories as they arrive;
  - show the latest active profile only;
  - keep user-visible warnings brief and Russian.

- [ ] Update view helpers to render:
  - current phase text;
  - partial-research warnings;
  - normalized category labels;
  - no raw provenance.

- [ ] Write launcher tests that verify:

```python
def test_research_live_mode_streams_categories_to_state():
    ...

def test_research_quiet_mode_hides_stream_until_completion():
    ...

def test_launcher_shows_russian_phase_labels():
    ...
```

- [ ] Run launcher tests.

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_desktop_launcher_controller.py tests/test_desktop_view_helpers.py tests/test_desktop_launcher.py -v`
Expected: PASS.

- [ ] Commit the launcher slice.

```bash
git add launcher/desktop_controller.py launcher/desktop_view_helpers.py launcher/desktop_window_sections.py launcher/desktop_ui_text.py launcher/desktop_launcher.py tests/test_desktop_launcher_controller.py tests/test_desktop_view_helpers.py tests/test_desktop_launcher.py
git commit -m "feat: integrate live catalog research into launcher"
```

### Task 7: Verification And Regression Gate

**Files:**
- Modify: `docs/LAUNCHER_ARCHITECTURE.md`
- Modify: `docs/NEXT_STEPS.md`
- Modify: `docs/PROJECT_STATE.md`
- Test: `tests/test_architecture_check.py`

- [ ] Update docs so the implemented research core becomes the documented source of truth.

- [ ] Add or update architecture-check coverage so the new discovery-core files stay within architecture rules.

- [ ] Run the full verification suite.

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: PASS.

Run: `.\.venv\Scripts\python.exe -m compileall -q main.py models parsers policies strategies utils scripts tests launcher`
Expected: no output.

Run: `.\.venv\Scripts\python.exe scripts\architecture_check.py`
Expected: `Architecture check passed: no findings.`

Run: `.\.venv\Scripts\python.exe scripts\\run_desktop_launcher.py --smoke`
Expected: `Desktop launcher smoke passed.`

- [ ] Commit the docs and verification slice.

```bash
git add docs/LAUNCHER_ARCHITECTURE.md docs/NEXT_STEPS.md docs/PROJECT_STATE.md tests/test_architecture_check.py
git commit -m "docs: finalize catalog research core architecture"
```

## Spec Coverage Check

This plan covers:

- adaptive `Исследование` pipeline;
- legacy Pyaterochka runtime reference without coupling the new core to it;
- rich internal discovery graph;
- latest-profile UI with internal history retention;
- live phased progress and quiet mode;
- Russian launcher UX;
- storage-agnostic profile persistence;
- groundwork for later product filters and selection without implementing the whole next subsystem now.

This plan intentionally leaves for the next plan:

- explicit product selection before report export;
- deep “Дополнительно найденные фильтры” derivation beyond compatibility;
- broader multi-store strategy learning from saved provenance.

## Placeholder Scan

No task in this plan relies on `TBD`, `TODO`, “implement later”, or references to undefined files. The only deferred items are explicitly called out in `Scope Split` as out of scope for this implementation plan.

## Type Consistency Check

Core types referenced across tasks are consistent:

- `DiscoveryNode`
- `SiteProfileVersion`
- `DiscoveryPhaseEvent`
- `LauncherResearchState`
- `DiscoveryProfileRepository`
- `run_catalog_tree_discovery(...)`

These names should remain stable during implementation unless the entire plan is revised together.
