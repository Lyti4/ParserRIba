# ParserRIba Next Steps

Date: 2026-05-15

## Active Track

The active track is now split into two coupled layers:

1. keep Pyaterochka data interception and API-first extraction stable;
2. rebuild the desktop launcher around a strict discovery-first user flow:
   - research store;
   - choose discovered sections;
   - collect products;
   - narrow the selection;
   - build the final report.

Architecture and delivery decisions for this stage are tracked in
`docs/ROADMAP_V1.md`. Use this file for the main roadmap; use this document for
the current active execution track.

## Immediate Plan

Detailed launcher rebuild plan:

- `docs/LAUNCHER_ARCHITECTURE.md`
- `docs/superpowers/plans/2026-05-22-launcher-discovery-first-rebuild.md`

1. Keep the current local task layer stable:
   - onboarding discovery;
   - Pyaterochka fish export;
   - Pyaterochka wine export;
   - report export from SQLite;
   - report filter options.
2. Keep the unified launcher-facing result contract stable:
   - `LocalTaskProcessResult`;
   - first-class `report_summary`, `export_summary`,
     `available_filter_counts`, `category_tree`, `catalog_discovery`;
   - unified `launcher_view`.
3. Make the launcher category UI discovery-first:
   - no injected categories before store research;
   - no auto-selected categories;
   - visible action name `Исследование`.
4. First usable launcher flow must support:
   - choose store URL and intent;
   - research catalog structure;
   - choose discovered sections;
   - collect products by chosen sections;
   - choose filters from real collected data;
   - build report and open Excel / report folder / JSON.
5. Keep Pyaterochka runtime stable while the launcher layer is added:
   launcher export must reuse the existing Pyaterochka local task/backend path
   with Camoufox, RU proxy/GeoIP, persistent profile/session behavior,
   human-like behavior, safe interception, API-first candidates, DOM fallback
   and anti-bot/proxy/error reporting.
6. Continue using SQLite as the main desktop storage.
7. Defer installer/update work until the launcher MVP is usable end-to-end.

## Next Refactors

- Add launcher state models:
  - selection state;
  - filter state;
  - task state;
  - result state.
- Keep `parsers/base.py` as the canonical active parser contract.
- Keep legacy parser modules quarantined from active runtime.
- Move more store-specific route and API markers into each store KB file as
  those stores are stabilized.
- Keep installer/update work out of the active code path until GUI MVP exists.

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q main.py models parsers policies strategies utils scripts tests
.\.venv\Scripts\python.exe scripts\architecture_check.py
```

## Manual Smoke Commands

Visual Pyaterochka check:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_pyaterochka_visual.ps1
```

Passive API discovery:

```powershell
.\.venv\Scripts\python.exe scripts\discover_pyaterochka_api.py --listen-seconds 180
```

## Later Roadmap

1. PyInstaller portable build.
2. Inno Setup installer.
3. GitHub Releases delivery flow.
4. One more real store after launcher MVP is stable.
5. Scheduler/background runs after multi-store stability.
6. Server/backend work only after the desktop product is genuinely useful.
