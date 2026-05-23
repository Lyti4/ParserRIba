# Camoufox Research Walker Implementation Plan

> **Status:** Superseded for Launcher V2 planning. Keep this file as
> implementation history for the Camoufox walker slice only.
> Current source of truth:
> `docs/superpowers/specs/2026-05-23-launcher-v2-discovery-workflow-design.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the next production slice of `Исследование`: a real active browser walker for catalog/menu discovery that is designed around Camoufox's actual capabilities and limits.

**Architecture:** Keep the discovery core independent from the legacy Pyaterochka runtime, but make the browser layer explicitly Camoufox-aware. The walker must use one serial browser session, one active page, explicit `goto` navigation, menu expansion, DOM/network evidence collection, and short listing validation runs. Do not build the walker around multi-page concurrency, `go_back()` history dependence, or experimental remote-server features.

**Tech Stack:** Python 3.11, asyncio, Camoufox async API, Playwright-compatible page events, Pydantic v2, SQLite, PySide6, pytest.

---

## Camoufox Constraints That Drive This Plan

This plan is based on the current official Camoufox repo and docs:

- `AsyncCamoufox` is Playwright-compatible and can launch a persistent context when `persistent_context=True` and `user_data_dir` is provided.
- `geoip=True` is intended to align geolocation, timezone, locale, and WebRTC IP with the proxy exit IP.
- `humanize=True` or a float duration uses Camoufox cursor humanization.
- `enable_cache` is disabled by default, and without it `page.go_back()` / `page.go_forward()` should not be part of the walker design.
- `disable_coop=True` exists and can help with cross-origin iframe interaction, including challenge widgets, but should stay opt-in.
- `config={...}` is an advanced escape hatch, not the primary integration surface.
- Remote server mode is explicitly experimental and should not be part of ParserRIba runtime design.
- There is a known issue history around multiple async pages freezing, so the walker should stay serial and single-page-first.

## File Map

- `docs/superpowers/specs/2026-05-22-catalog-tree-discovery-design.md`
  - update Phase 1-4 wording to match the Camoufox-aware walker design.
- `docs/NEXT_STEPS.md`
  - point the active execution track at the walker slice after the current state-model/storage groundwork.
- `utils/camoufox_launcher.py`
  - centralize research-specific Camoufox options instead of scattering them across discovery scripts.
- `utils/browser_catalog_discovery.py`
  - stop acting like a single-page snapshot helper and become the public entrypoint into the active walker.
- `utils/catalog_tree_discovery/camoufox_runtime_profile.py`
  - new focused policy object for research launch options and guardrails.
- `utils/catalog_tree_discovery/event_capture.py`
  - new response/request capture helpers for category-tree discovery.
- `utils/catalog_tree_discovery/entrypoint_collectors.py`
  - new DOM collectors for header menu, burger menu, breadcrumbs, sidebar, and inline catalog surfaces.
- `utils/catalog_tree_discovery/menu_expander.py`
  - new safe menu expansion helpers for hover/click/open-close behavior.
- `utils/catalog_tree_discovery/research_queue.py`
  - new serial queue and dedup rules for candidate node exploration.
- `utils/catalog_tree_discovery/research_walker.py`
  - new active walker that drives one page through discovery phases.
- `utils/catalog_tree_discovery/listing_validator.py`
  - extend classification into a short active validation probe.
- `utils/catalog_tree_discovery/runner.py`
  - call the new walker and expose phase events that reflect real work.
- `utils/site_onboarding.py`
  - continue to call the runner, but now consume richer streamed status and warnings.
- `launcher/desktop_controller_research.py`
  - map richer research phases into launcher-safe state.
- `launcher/desktop_view_helpers.py`
  - render phase text and partial-result warnings from the walker.
- `launcher/desktop_ui_text.py`
  - centralize Russian labels for new phases and warnings.
- `tests/test_browser_catalog_discovery.py`
  - replace snapshot-style expectations with walker-style expectations.
- `tests/test_catalog_tree_discovery_runner.py`
  - verify queue limits, phase events, partial challenge state, and validation behavior.
- `tests/test_site_onboarding.py`
  - verify onboarding still surfaces launcher-safe trees from the new walker.
- `tests/test_camoufox_launcher.py`
  - add research-specific Camoufox option coverage.
- `tests/test_desktop_view_helpers.py`
  - verify Russian phase rendering and partial warnings.

## Scope Split

This plan intentionally focuses on the browser walker for `Исследование`.

This plan does **not** implement:

- full product extraction from selected categories;
- store-specific strategy learning beyond storing signals and warnings;
- automatic captcha solving;
- multi-browser or multi-page parallel research;
- remote Camoufox server deployment.

Those stay outside this slice.

### Task 1: Freeze The Camoufox Research Contract

**Files:**
- Create: `utils/catalog_tree_discovery/camoufox_runtime_profile.py`
- Modify: `utils/camoufox_launcher.py`
- Test: `tests/test_camoufox_launcher.py`

- [ ] **Step 1: Write the failing tests for research launch options**

```python
from utils.camoufox_launcher import build_research_camoufox_options


def test_build_research_camoufox_options_uses_serial_research_defaults(tmp_path) -> None:
    options = build_research_camoufox_options(
        headless=False,
        proxy_url="http://user:pass@example:8080",
        geoip=True,
        user_data_dir=tmp_path / "profile",
    )

    assert options["persistent_context"] is True
    assert options["humanize"] == 1.5
    assert options["block_images"] is False
    assert options["block_webgl"] is False
    assert options["locale"] == "ru-RU"


def test_build_research_camoufox_options_does_not_enable_cache_or_remote_only_flags() -> None:
    options = build_research_camoufox_options(headless=True)

    assert "enable_cache" not in options
    assert "ws_endpoint" not in options
```

- [ ] **Step 2: Run the targeted tests to confirm the helper does not exist yet**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_camoufox_launcher.py -v`
Expected: FAIL with `ImportError` or missing `build_research_camoufox_options`.

- [ ] **Step 3: Add the focused research runtime profile**

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CamoufoxResearchRuntimeProfile:
    locale: str = "ru-RU"
    humanize: float = 1.5
    block_images: bool = False
    block_webgl: bool = False
    require_persistent_context: bool = True
    allow_disable_coop: bool = False
```

```python
def build_research_camoufox_options(
    *,
    headless: bool | str,
    proxy_url: str | None = None,
    geoip: bool = False,
    user_data_dir: str | Path | None = None,
    profile: CamoufoxResearchRuntimeProfile | None = None,
) -> dict[str, Any]:
    runtime = profile or CamoufoxResearchRuntimeProfile()
    return build_camoufox_options(
        headless=headless,
        proxy_url=proxy_url,
        geoip=geoip,
        block_images=runtime.block_images,
        block_webgl=runtime.block_webgl,
        humanize=runtime.humanize,
        locale=runtime.locale,
        fingerprint_os="windows",
        user_data_dir=user_data_dir if runtime.require_persistent_context else None,
    )
```

- [ ] **Step 4: Run the targeted tests to verify the contract**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_camoufox_launcher.py -v`
Expected: PASS for the new research-option tests.

- [ ] **Step 5: Commit the launch-contract slice**

```bash
git add utils/camoufox_launcher.py utils/catalog_tree_discovery/camoufox_runtime_profile.py tests/test_camoufox_launcher.py
git commit -m "feat: add camoufox research runtime profile"
```

### Task 2: Add Event Capture For Discovery Runs

**Files:**
- Create: `utils/catalog_tree_discovery/event_capture.py`
- Modify: `utils/browser_catalog_discovery.py`
- Test: `tests/test_browser_catalog_discovery.py`

- [ ] **Step 1: Write the failing tests for request/response capture**

```python
from utils.catalog_tree_discovery.event_capture import DiscoveryEventCapture


async def test_discovery_event_capture_records_catalog_like_requests() -> None:
    capture = DiscoveryEventCapture()

    await capture.record_request("https://shop.example/api/catalog/tree")
    await capture.record_response(
        url="https://shop.example/api/catalog/tree",
        status=200,
        content_type="application/json",
        body_text='{"items":[{"name":"Рыба"}]}',
    )

    assert capture.route_hints
    assert capture.route_hints[0].kind == "response_json"
```

- [ ] **Step 2: Run the tests to confirm the capture helper is missing**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_browser_catalog_discovery.py -v`
Expected: FAIL with missing module or symbol.

- [ ] **Step 3: Implement a focused discovery event sink**

```python
class DiscoveryEventCapture:
    def __init__(self) -> None:
        self.route_hints: list[RouteHint] = []
        self.request_urls: list[str] = []

    async def record_request(self, url: str) -> None:
        lowered = str(url).casefold()
        if any(marker in lowered for marker in ("/api/", "graphql", "/catalog", "/category")):
            self.request_urls.append(url)

    async def record_response(
        self,
        *,
        url: str,
        status: int,
        content_type: str,
        body_text: str,
    ) -> None:
        lowered = f"{url} {content_type}".casefold()
        if status >= 400:
            return
        if "json" not in lowered and "graphql" not in lowered:
            return
        if any(marker in body_text.casefold() for marker in ("category", "catalog", "breadcrumb", "children")):
            self.route_hints.append(RouteHint(kind="response_json", value=url, source="network"))
```

- [ ] **Step 4: Run the tests to verify passive capture**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_browser_catalog_discovery.py -v`
Expected: PASS for event-capture tests.

- [ ] **Step 5: Commit the event-capture slice**

```bash
git add utils/catalog_tree_discovery/event_capture.py utils/browser_catalog_discovery.py tests/test_browser_catalog_discovery.py
git commit -m "feat: add discovery network event capture"
```

### Task 3: Add Catalog Entrypoint Collectors And Menu Expansion

**Files:**
- Create: `utils/catalog_tree_discovery/entrypoint_collectors.py`
- Create: `utils/catalog_tree_discovery/menu_expander.py`
- Test: `tests/test_catalog_tree_discovery_runner.py`

- [ ] **Step 1: Write the failing tests for entrypoint extraction**

```python
from utils.catalog_tree_discovery.entrypoint_collectors import collect_catalog_entrypoints_from_html


def test_collect_catalog_entrypoints_prefers_menu_and_catalog_surfaces() -> None:
    html = """
    <nav>
      <a href="/catalog/fish">Рыба</a>
      <a href="/catalog/seafood">Морепродукты</a>
    </nav>
    """

    result = collect_catalog_entrypoints_from_html("https://shop.example", html)

    assert [item.name for item in result] == ["Рыба", "Морепродукты"]
```

- [ ] **Step 2: Run the tests to confirm collectors are missing**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_catalog_tree_discovery_runner.py -v`
Expected: FAIL with missing collector module.

- [ ] **Step 3: Implement menu-first entrypoint collection and safe expansion helpers**

```python
def collect_catalog_entrypoints_from_html(site_url: str, html: str) -> list[CategoryEvidence]:
    signals = collect_catalog_surface_signals(
        site_url=site_url,
        final_url=site_url,
        status_code=200,
        html=html,
    )
    return signals.dom_categories
```

```python
async def expand_menu_surfaces(page: Any) -> None:
    selectors = (
        "button[aria-expanded='false']",
        "[data-testid*='menu'] button",
        "button[class*='burger']",
        "button[class*='catalog']",
    )
    for selector in selectors:
        locator = page.locator(selector)
        count = await locator.count()
        for index in range(min(count, 5)):
            item = locator.nth(index)
            try:
                await item.hover(timeout=1_500)
                await page.wait_for_timeout(300)
                await item.click(timeout=1_500)
                await page.wait_for_timeout(500)
            except Exception:
                continue
```

- [ ] **Step 4: Run the tests to verify deterministic entrypoint collection**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_catalog_tree_discovery_runner.py -v`
Expected: PASS for the new entrypoint test.

- [ ] **Step 5: Commit the menu-entrypoint slice**

```bash
git add utils/catalog_tree_discovery/entrypoint_collectors.py utils/catalog_tree_discovery/menu_expander.py tests/test_catalog_tree_discovery_runner.py
git commit -m "feat: add catalog entrypoint collectors"
```

### Task 4: Build The Serial Research Queue

**Files:**
- Create: `utils/catalog_tree_discovery/research_queue.py`
- Test: `tests/test_catalog_tree_discovery_runner.py`

- [ ] **Step 1: Write the failing tests for dedup and repeat limits**

```python
from utils.catalog_tree_discovery.research_queue import ResearchQueue


def test_research_queue_deduplicates_urls_and_respects_repeat_limit() -> None:
    queue = ResearchQueue(max_repeat_urls=2)

    assert queue.push("https://shop.example/catalog/fish") is True
    assert queue.push("https://shop.example/catalog/fish") is True
    assert queue.push("https://shop.example/catalog/fish") is False
```

- [ ] **Step 2: Run the tests to confirm the queue is missing**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_catalog_tree_discovery_runner.py -v`
Expected: FAIL with missing `ResearchQueue`.

- [ ] **Step 3: Implement a single-threaded research queue**

```python
from collections import deque


class ResearchQueue:
    def __init__(self, *, max_repeat_urls: int) -> None:
        self.max_repeat_urls = max_repeat_urls
        self._queue: deque[str] = deque()
        self._counts: dict[str, int] = {}

    def push(self, url: str) -> bool:
        count = self._counts.get(url, 0)
        if count >= self.max_repeat_urls:
            return False
        self._counts[url] = count + 1
        self._queue.append(url)
        return True

    def pop(self) -> str | None:
        if not self._queue:
            return None
        return self._queue.popleft()
```

- [ ] **Step 4: Run the queue tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_catalog_tree_discovery_runner.py -v`
Expected: PASS for queue tests.

- [ ] **Step 5: Commit the queue slice**

```bash
git add utils/catalog_tree_discovery/research_queue.py tests/test_catalog_tree_discovery_runner.py
git commit -m "feat: add serial research queue"
```

### Task 5: Implement The Active Camoufox Research Walker

**Files:**
- Create: `utils/catalog_tree_discovery/research_walker.py`
- Modify: `utils/browser_catalog_discovery.py`
- Modify: `utils/catalog_tree_discovery/runner.py`
- Test: `tests/test_browser_catalog_discovery.py`
- Test: `tests/test_catalog_tree_discovery_runner.py`

- [ ] **Step 1: Write the failing tests for active phase progression**

```python
async def test_research_walker_emits_real_phases_and_collects_categories(monkeypatch) -> None:
    walker = CamoufoxResearchWalker(...)

    result = await walker.run("https://shop.example/catalog")

    assert result.phase_events[0].phase == "open_site"
    assert any(event.phase == "expand_menu" for event in result.phase_events)
    assert result.catalog_discovery.category_links
```

- [ ] **Step 2: Run the tests to confirm the walker does not exist**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_browser_catalog_discovery.py tests/test_catalog_tree_discovery_runner.py -v`
Expected: FAIL with missing walker and missing phase.

- [ ] **Step 3: Implement a serial single-page walker**

```python
class CamoufoxResearchWalker:
    def __init__(self, *, listen_seconds: int, max_repeat_urls: int, max_depth: int) -> None:
        self.listen_seconds = listen_seconds
        self.queue = ResearchQueue(max_repeat_urls=max_repeat_urls)
        self.max_depth = max_depth

    async def run(self, site_url: str, page: Any) -> CatalogTreeDiscoveryRunResult:
        phase_events = [make_phase_event("open_site", "running", "Открытие сайта")]
        response = await page.goto(site_url, wait_until="domcontentloaded", timeout=60_000)
        phase_events.append(make_phase_event("expand_menu", "running", "Раскрытие меню"))
        await expand_menu_surfaces(page)
        await page.wait_for_timeout(self.listen_seconds * 1000)
        html = await page.content()
        discovery = summarize_catalog_discovery(
            site_url=site_url,
            final_url=page.url or site_url,
            status_code=response.status if response else 0,
            html=html,
        )
        return ...
```

- [ ] **Step 4: Run the walker tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_browser_catalog_discovery.py tests/test_catalog_tree_discovery_runner.py -v`
Expected: PASS for walker-phase tests.

- [ ] **Step 5: Commit the active-walker slice**

```bash
git add utils/catalog_tree_discovery/research_walker.py utils/browser_catalog_discovery.py utils/catalog_tree_discovery/runner.py tests/test_browser_catalog_discovery.py tests/test_catalog_tree_discovery_runner.py
git commit -m "feat: add active camoufox research walker"
```

### Task 6: Add Short Listing Validation Probes

**Files:**
- Modify: `utils/catalog_tree_discovery/listing_validator.py`
- Modify: `utils/catalog_tree_discovery/research_walker.py`
- Test: `tests/test_catalog_tree_discovery_runner.py`

- [ ] **Step 1: Write the failing tests for active validation states**

```python
def test_classify_listing_probe_distinguishes_menu_only_and_listing_valid() -> None:
    menu_only = classify_catalog_surface(SurfaceSignals(dom_categories=[...]))
    listing = classify_catalog_surface(SurfaceSignals(dom_products=[...]))

    assert menu_only.validation_state == "menu_only"
    assert listing.validation_state == "listing_valid"
```

- [ ] **Step 2: Run the tests to verify the current validator is insufficient**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_catalog_tree_discovery_runner.py -v`
Expected: FAIL on missing probe behavior or route-hint expectations.

- [ ] **Step 3: Extend validation to short active probes**

```python
async def validate_listing_candidate(page: Any, url: str, wait_ms: int = 2_500) -> ValidationProbeResult:
    response = await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    await page.wait_for_timeout(wait_ms)
    html = await page.content()
    signals = collect_catalog_surface_signals(
        site_url=url,
        final_url=page.url or url,
        status_code=response.status if response else 0,
        html=html,
    )
    return classify_catalog_surface(signals)
```

- [ ] **Step 4: Run the validator tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_catalog_tree_discovery_runner.py -v`
Expected: PASS for validation classification tests.

- [ ] **Step 5: Commit the validation slice**

```bash
git add utils/catalog_tree_discovery/listing_validator.py utils/catalog_tree_discovery/research_walker.py tests/test_catalog_tree_discovery_runner.py
git commit -m "feat: add listing validation probes"
```

### Task 7: Integrate Richer Research State Into Onboarding And Launcher

**Files:**
- Modify: `utils/site_onboarding.py`
- Modify: `launcher/desktop_controller_research.py`
- Modify: `launcher/desktop_view_helpers.py`
- Modify: `launcher/desktop_ui_text.py`
- Test: `tests/test_site_onboarding.py`
- Test: `tests/test_desktop_view_helpers.py`

- [ ] **Step 1: Write the failing tests for new Russian phases and warnings**

```python
def test_build_result_summary_shows_expand_menu_and_partial_warning() -> None:
    ...
    assert "Раскрытие меню" in summary
    assert "частично исследовано" in summary
```

- [ ] **Step 2: Run the tests to confirm the new UI text is missing**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_site_onboarding.py tests/test_desktop_view_helpers.py -v`
Expected: FAIL on missing phase labels and warning text.

- [ ] **Step 3: Add launcher-safe phase mapping**

```python
RESEARCH_PHASE_LABELS = {
    "open_site": "Открытие сайта",
    "expand_menu": "Раскрытие меню",
    "collect_surface": "Сбор структуры",
    "validate_nodes": "Проверка разделов",
    "persist_profile": "Сохранение профиля",
    "build_tree": "Подготовка дерева",
}
```

```python
if research.partial:
    diagnostics["warning"] = "частично исследовано"
```

- [ ] **Step 4: Run the onboarding and launcher-view tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_site_onboarding.py tests/test_desktop_view_helpers.py -v`
Expected: PASS for phase rendering and warning propagation.

- [ ] **Step 5: Commit the launcher-integration slice**

```bash
git add utils/site_onboarding.py launcher/desktop_controller_research.py launcher/desktop_view_helpers.py launcher/desktop_ui_text.py tests/test_site_onboarding.py tests/test_desktop_view_helpers.py
git commit -m "feat: expose camoufox research phases in launcher"
```

### Task 8: Update Docs And Run End-To-End Verification

**Files:**
- Modify: `docs/superpowers/specs/2026-05-22-catalog-tree-discovery-design.md`
- Modify: `docs/NEXT_STEPS.md`
- Test: `tests/test_browser_catalog_discovery.py`
- Test: `tests/test_catalog_tree_discovery_runner.py`
- Test: `tests/test_site_onboarding.py`
- Test: `tests/test_desktop_view_helpers.py`

- [ ] **Step 1: Update the design doc with Camoufox-specific rules**

```md
### Camoufox Walker Rules

- use one active page for discovery;
- do not rely on `page.go_back()` / `page.go_forward()`;
- keep discovery serial while Camoufox async multi-page behavior remains risky;
- keep remote server mode out of runtime scope;
- keep `config={...}` as an advanced fallback only.
```

- [ ] **Step 2: Run the focused validation suite**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_camoufox_launcher.py tests/test_browser_catalog_discovery.py tests/test_catalog_tree_discovery_runner.py tests/test_site_onboarding.py tests/test_desktop_view_helpers.py -q`
Expected: PASS.

- [ ] **Step 3: Run compile and architecture validation**

Run: `.\.venv\Scripts\python.exe -m compileall -q main.py models parsers policies strategies utils scripts tests`
Expected: no output.

Run: `.\.venv\Scripts\python.exe scripts\architecture_check.py`
Expected: `Architecture check passed: no findings.`

- [ ] **Step 4: Run launcher smoke**

Run: `.\.venv\Scripts\python.exe scripts\run_desktop_launcher.py --smoke`
Expected: `Desktop launcher smoke passed.`

- [ ] **Step 5: Commit the doc and verification slice**

```bash
git add docs/superpowers/specs/2026-05-22-catalog-tree-discovery-design.md docs/NEXT_STEPS.md
git commit -m "docs: add camoufox research walker plan"
```

## Spec Coverage Check

This plan covers:

- a true active walker instead of one passive page snapshot;
- Camoufox-specific launch policy and guardrails;
- serial navigation instead of unsafe async multi-page fan-out;
- menu expansion and entrypoint discovery;
- short listing validation probes;
- launcher-visible phase progress and partial warnings.

This plan intentionally leaves out:

- full selected-category product extraction;
- full filter derivation engine;
- strategy learning and auto-remediation;
- automatic captcha solving.

## Placeholder Scan

No task uses `TBD`, `TODO`, or unnamed follow-up work. Each task names exact files, test commands, and concrete implementation targets.

## Type Consistency Check

The new symbols introduced by this plan are consistent across tasks:

- `CamoufoxResearchRuntimeProfile`
- `build_research_camoufox_options(...)`
- `DiscoveryEventCapture`
- `ResearchQueue`
- `CamoufoxResearchWalker`
- `validate_listing_candidate(...)`
