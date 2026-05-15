# ParserRIba Next Steps

Date: 2026-05-15

## Active Track

The active track is Pyaterochka data interception and API-first extraction.
Avoid starting GUI, installer, FastAPI, Postgres, Redis or dashboard work until
the parser can reliably capture and normalize product data.

## Immediate Plan

1. Move Pyaterochka API route classification from the temporary store profile
   into `knowledge_base/` after KB loader cleanup.
2. Continue saving compact safe interception reports under `data/interception/`:
   masked URLs, route type, status, response size, payload preview, schema
   hints and sample products only.
3. Run visual/discovery with working RU proxy and manual captcha solving.
4. Inspect `Interception`, `Site Error Tracking`, `Proxy Diagnostics` and
   `Proxy History` report blocks.
5. Use the API-first candidate report to confirm real Pyaterochka product
   fields: id, name, price, product link, image and availability.
6. Build the final Pyaterochka `Product` mapper only after those fields are
   confirmed from real reports.
7. Keep DOM/card extraction as fallback for cases where API discovery fails.
8. Add local SQLite product and price-history storage after API payloads are
   understood.

## Next Refactors

- Split `scripts/smoke_pyaterochka_camoufox.py` into smaller modules.
- Replace legacy `utils/session_manager.py` with `utils.session_pool`.
- Pick one canonical parser base contract and fix `ParserFactory` import
  warnings for non-Pyaterochka stores.
- Remove legacy tracked artifacts from Git permanently: logs and `__pycache__`
  were already removed from the latest pushed commit.

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

1. SQLite product and price history.
2. Data normalization and deduplication.
3. FastAPI after data is useful.
4. Postgres/Alembic after schema is proven locally.
5. Workers/scheduler after multiple stores are stable.
6. Observability integrations after local diagnostics mature.
7. Dashboard and installer after parser reliability improves.
