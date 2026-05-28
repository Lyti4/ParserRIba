# Launcher Data Flow Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Launcher V2 resilient by separating GUI rendering, launcher state, background actions, local tasks, browser runtime, storage and artifacts.

**Architecture:** The launcher keeps a one-way data flow: GUI starts actions, workers/subprocesses return data, GUI-thread callbacks apply state and render widgets. Browser/runtime code never imports desktop UI, and UI code never touches browser handles.

**Tech Stack:** Python 3.11, PySide6, Pydantic v2 launcher state, QThread background actions, local task subprocesses, Camoufox async runtime.

---

## File Structure

- Canonical rules: `docs/DATA_FLOW_THREADING_PLAN.md`
- Architecture index: `docs/TARGET_ARCHITECTURE.md`
- Launcher flow reference: `docs/LAUNCHER_ARCHITECTURE.md`
- Next work queue: `docs/NEXT_STEPS.md`
- Current background runner: `launcher/desktop_background_task.py`
- State contract: `models/launcher_state.py`
- Workspace merge logic: `launcher/desktop_controller_workspace.py`
- Current thread regression test: `tests/test_desktop_background_task.py`

## Task 1: Keep Thread Boundary Document Current

**Files:**
- Modify: `docs/DATA_FLOW_THREADING_PLAN.md`
- Modify: `docs/TARGET_ARCHITECTURE.md`
- Modify: `docs/LAUNCHER_ARCHITECTURE.md`
- Modify: `docs/NEXT_STEPS.md`

- [x] **Step 1: Review the canonical invariant**

Open `docs/DATA_FLOW_THREADING_PLAN.md` and verify it still says:

```text
Workers, subprocesses and browser runtimes return data. Only the GUI thread renders widgets.
```

- [x] **Step 2: Link new architecture work to the invariant**

When adding launcher/product/filter/report behavior, update the relevant doc
section with one sentence that points back to
`docs/DATA_FLOW_THREADING_PLAN.md`.

- [x] **Step 3: Check docs only**

Run:

```powershell
git diff --check -- docs
```

Expected: no whitespace errors.

- [x] **Step 4: Commit the documentation slice**

Run:

```powershell
git add docs/DATA_FLOW_THREADING_PLAN.md docs/TARGET_ARCHITECTURE.md docs/LAUNCHER_ARCHITECTURE.md docs/NEXT_STEPS.md docs/superpowers/plans/2026-05-28-launcher-data-flow-isolation.md
git commit -m "docs: define launcher data flow boundaries"
```

Expected: commit succeeds.

## Task 2: Protect GUI Thread Callback Contract

**Files:**
- Modify: `launcher/desktop_background_task.py`
- Test: `tests/test_desktop_background_task.py`

- [x] **Step 1: Keep callbacks in GUI-thread QObject slots**

Verify `start_background_action(...)` creates a retained callback object whose
slots live in the GUI thread. The shape must remain equivalent to:

```python
callbacks = _Callbacks(on_finished=on_finished, on_failed=on_failed, on_cleared=on_cleared)
callbacks.moveToThread(qtcore.QCoreApplication.instance().thread())
worker.finished.connect(callbacks.handle_finished)
worker.failed.connect(callbacks.handle_failed)
thread.finished.connect(callbacks.handle_cleared)
thread._parserriba_callbacks = callbacks
```

- [x] **Step 2: Preserve thread-affinity regression test**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_desktop_background_task.py
```

Expected: test proves the action runs in the worker thread while callbacks run
on the GUI thread.

- [ ] **Step 3: Add a new test before changing the runner**

Any future runner change must add a failing test that reproduces the desired
thread behavior before implementation.

## Task 3: Add Typed Progress Events Before Live Streaming

**Files:**
- Modify: `models/launcher_state.py`
- Create: `models/launcher_progress.py`
- Modify: `launcher/desktop_background_task.py`
- Test: `tests/test_launcher_progress.py`

- [x] **Step 1: Define the event contract**

Create `models/launcher_progress.py` with an immutable event model:

```python
from pydantic import BaseModel, ConfigDict


class LauncherProgressEvent(BaseModel):
    """Immutable launcher progress event emitted by workers."""

    model_config = ConfigDict(frozen=True)

    task_kind: str
    phase: str
    message: str
    current: int | None = None
    total: int | None = None
```

- [x] **Step 2: Write the unit test**

Create `tests/test_launcher_progress.py`:

```python
from models.launcher_progress import LauncherProgressEvent


def test_launcher_progress_event_is_immutable() -> None:
    event = LauncherProgressEvent(
        task_kind="product_export",
        phase="collect_products",
        message="Сбор товаров",
        current=1,
        total=3,
    )

    assert event.task_kind == "product_export"
    assert event.current == 1
    try:
        event.current = 2
    except Exception as exc:
        assert "frozen" in str(exc).lower()
    else:
        raise AssertionError("LauncherProgressEvent must be immutable")
```

- [x] **Step 3: Run the focused test**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_launcher_progress.py
```

Expected: pass.

- [ ] **Step 4: Wire progress only through GUI-thread callbacks**

Add progress streaming only after the immutable event model exists. The worker
may emit `LauncherProgressEvent`; the GUI-thread callback slot applies it to
`LauncherAppState`.

## Task 4: Keep Product Workspace One-Way

**Files:**
- Modify: `launcher/desktop_controller_workspace.py`
- Modify: `launcher/desktop_result_table.py`
- Modify: `launcher/desktop_dynamic_filter_panel.py`
- Test: `tests/test_desktop_launcher_controller.py`
- Test: `tests/test_desktop_result_table.py`
- Test: `tests/test_desktop_filter_panel.py`

- [ ] **Step 1: Verify product state source**

Confirm `state.products.items` remains the first source for the `Товары` tab,
product details and filter derivation.

- [ ] **Step 2: Add failing tests for new product behavior**

Before changing product collection or filters, add tests for:

```text
selected catalog node URLs reach product collection
multiple selected nodes merge into one product workspace
filters derive from collected raw fields
report export receives selected product ids
```

- [ ] **Step 3: Run focused launcher tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_desktop_launcher_controller.py tests/test_desktop_result_table.py tests/test_desktop_filter_panel.py
```

Expected: pass.

## Task 5: Verification Gate

**Files:**
- No code files required unless earlier tasks changed them.

- [x] **Step 1: Run full tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: pass.

- [x] **Step 2: Compile active compatibility surface**

Run:

```powershell
.\.venv\Scripts\python.exe -m compileall -q main.py models parsers policies strategies utils scripts tests
```

Expected: no compile errors.

- [x] **Step 3: Run architecture check**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\architecture_check.py
```

Expected: no errors. Known long-test warnings should be handled in the next
hygiene slice, not ignored indefinitely.

- [x] **Step 4: Run launcher smoke**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_desktop_launcher.py --smoke
```

Expected: smoke command exits successfully.

## Self-Review

- Spec coverage: covers GUI thread, background thread, local task subprocess,
  browser runtime, storage, product workspace, filtering and report boundaries.
- Placeholder scan: no `TBD`, `TODO`, or undefined future code is required for
  the current documentation slice.
- Type consistency: future progress event uses a dedicated Pydantic model and
  does not pass Qt objects across worker boundaries.
