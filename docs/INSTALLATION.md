# ParserRIba Installation Strategy

## V1: Local Windows Application

ParserRIba v1 is a local-first Windows application. The launcher runs local
tasks through the ParserRIba task layer; scraping logic stays in store backends,
and reports are written locally.

Runtime layout:

- `data/` - SQLite databases, JSON exports, Excel reports, manifests.
- `profiles/` - local browser profiles.
- `logs/` - local logs.
- `knowledge_base/` - store-specific URLs, category names and rules.
- `.venv/` - development virtual environment.

Development install:

```powershell
cd C:\tmp\ParserRIba-clean
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
```

User install target:

- portable zip or Windows installer;
- bundled launcher and dependency bootstrap;
- first-run setup for profile path, output path, optional proxy and Camoufox
  check;
- all generated data remains local by default.

## V2: Remote/Server Mode

Remote mode is deferred until at least Pyaterochka plus one more retailer are
stable. The server version should reuse the same local task registry instead of
rewriting scraping logic.

Expected server pieces:

- API layer for users and task submission;
- worker nodes that run the same local tasks;
- shared storage, likely Postgres after SQLite schemas are proven;
- queue and scheduling layer;
- proxy/session health layer.

Do not add paid scraping, captcha, browser or cloud services without explicit
approval.

## Launcher Contract

Launcher code should not call store scripts directly. It should call
`utils.launcher_task_controller`, which routes work through local tasks and
returns a machine-readable run manifest.

Current launcher actions:

- onboarding discovery;
- Pyaterochka fish export;
- Pyaterochka wine export;
- filtered Excel report export from SQLite.

