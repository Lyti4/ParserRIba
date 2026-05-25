# ParserRIba Agent Guide

You are working on ParserRIba in `C:\tmp\ParserRIba-clean`.

Read these files first in any new chat or automation:

1. `AGENTS.md`
2. `docs/PROJECT_STATE.md`
3. `docs/NEXT_STEPS.md`
4. `docs/ROADMAP_V1.md`
5. `docs/TARGET_ARCHITECTURE.md`
6. `docs/PROJECT_STRUCTURE.md`
7. `docs/TOOLS_POLICY.md`
8. `docs/AUTOMATIONS.md`
9. `docs/ARCHITECTURE_STEWARD.md`

## Project Rules

- Python 3.10+, asyncio-first.
- Browser runtime is Camoufox through async Playwright-compatible APIs.
- Keep URLs, selectors and store rules in `knowledge_base/`.
- Use Pydantic v2 models and loguru logging.
- Do not add paid services, cloud LLMs, captcha-solving services or external
  APIs without explicit user approval.
- Do not commit secrets, `.env`, proxy credentials, browser profiles, cookies,
  captcha tokens, `GeoLite2-City.mmdb`, logs, `data/`, `dist/`, `build/`,
  `__pycache__/` or `.pyc`.

## Hard Constraints

- Do not call `.get()` on Pydantic model instances. Use attributes,
  `getattr(...)`, or `model_dump(...)`.
- Do not call `.close()` on `AsyncCamoufox` / `Camoufox`. Use `async with` or
  `__aexit__`.
- Do not use `time.sleep()`. Use `asyncio.sleep()` or browser wait APIs.
- Do not use `print()` for logs in runtime code. Use loguru.
- Keep new focused Python modules below 300 lines when practical.
- For orchestration entrypoints and large tests, up to roughly 450 lines is
  acceptable if the file still has one clear responsibility.

## Current Focus

The current product direction is launcher-first. ParserRIba is being organized
as a local desktop program with separate cores for browser/discovery/catalog,
products, filters, reports, storage and store profiles.

Current priorities:

1. Keep the launcher-first workflow as the canonical user path.
2. Keep Pyaterochka protected-store mechanics available through a store adapter.
3. Improve store-neutral discovery and catalog tree/profile storage.
4. Collect full product cards from explicitly selected catalog nodes.
5. Build dynamic filters and reports from collected product data.

The old CLI/parser stack is not a product runtime. Keep it only as temporary
reference until useful mechanics are extracted and the files can move to
`archive/`.

## Validation

Run from `C:\tmp\ParserRIba-clean`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q main.py models parsers policies strategies utils scripts tests
.\.venv\Scripts\python.exe scripts\architecture_check.py
```

Expected current state: tests pass, compile succeeds, architecture check has no
errors but still reports known legacy warnings. `main.py`, `parsers/`,
`policies/` and `strategies/` are compiled as compatibility surface only until
their useful mechanics are extracted and the legacy files are archived.
