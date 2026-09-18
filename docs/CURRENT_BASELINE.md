# Current Baseline

Date: 2026-06-16

## Workspace

- Primary Windows runtime workspace: `C:\tmp\ParserRIba-clean`
- Current Linux mirror/workspace on Hermes server: `/home/hermesadmin/work/ParserRIba-clean`
- Current branch observed on the Linux mirror: `codex/catalog-tree-discovery-core`
- Remote: `https://github.com/Lyti4/ParserRIba.git`

## Why this baseline exists

The project now has a large dirty working tree with many modified and untracked
files. Before adding big features, every new slice should start from a known
validation strategy:

1. Linux CI proves code quality, encoding, architecture and non-GUI contracts.
2. Windows local validation proves the launcher, visible browser, manual captcha
   flow, Camoufox and PySide6 behavior.
3. Git/GitHub is used for history, backup and review, while the Windows local
   workspace remains the authoritative runtime environment.

## Current product direction

ParserRIba is a launcher-first local Windows desktop program.

Canonical user flow:

```text
Исследование -> Каталог -> Товары -> Отчёт -> Профиль/История
```

Canonical architecture:

```text
Launcher -> Task Orchestrator -> Browser/Discovery Core -> Store Adapter -> Product Core -> Filter Core -> Report Core -> Storage/Profile Core
```

Pyaterochka is the first runtime-ready protected-store adapter. Unknown or new
stores stay `discovery_only` until a real adapter is added.

## Linux-safe validation

Linux/headless checks should avoid pretending to validate the real Windows GUI.
They are responsible for:

- syntax and import compilation;
- encoding guard coverage;
- architecture guard coverage;
- focused tests that do not require real Windows desktop interaction;
- non-GUI contracts for discovery, manual wait logic, local agent tooling and
  report/data helpers.

Current Linux-safe GitHub Actions workflow runs:

```bash
python -m compileall -q models utils scripts tests stores launcher
python scripts/agent_ops_check.py --scope all --with-tests
python -m pytest -q \
  tests/test_agent_ops_check.py \
  tests/test_api_first_extractor.py \
  tests/test_catalog_discovery.py \
  tests/test_browser_manual_wait.py \
  tests/test_codex_rlm_sidecar.py
```

This intentionally replaces the old `pytest tests/` Linux job because PySide6
GUI/headless tests can segfault or abort on the Linux server even when the
Windows launcher path is the actual target runtime.

## Windows validation

Windows remains required for anything user-visible:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q models utils scripts tests stores launcher
.\.venv\Scripts\python.exe scripts\architecture_check.py
.\.venv\Scripts\python.exe scripts\run_desktop_launcher.py --smoke
.\.venv\Scripts\python.exe scripts\run_windows_validation.ps1
```

Manual browser/captcha validation should happen on the Windows desktop where the
user can see Camoufox, solve challenges and confirm the browser reached the
expected store/catalog/product state.

## Current remote-control status

- Hermes Telegram gateway works.
- HTTP/Codex tunnel on `127.0.0.1:19120` was observed working from the VPS.
- SSH reverse tunnel `127.0.0.1:2222 -> Windows 127.0.0.1:22` was not active
  during the latest check (`Connection refused`).

Until SSH or a Windows self-hosted GitHub runner is active, Hermes can safely
prepare code and Linux checks, but cannot directly drive PowerShell or visually
confirm the Windows desktop launcher.

## Next safe slices

1. Keep the CI split: Linux-safe guards in GitHub, Windows validation on the
   desktop/runtime workspace.
2. Bring up either the reverse SSH tunnel or a Windows self-hosted GitHub Actions
   runner.
3. Run the Windows validation script and capture UTF-8 logs.
4. Only then take launcher/browser/manual-captcha changes as product-complete.
5. Continue small feature slices: Pyaterochka end-to-end stabilization,
   responsive launcher polish, richer product-card extraction, report columns
   and StoreProfile/session hardening.
