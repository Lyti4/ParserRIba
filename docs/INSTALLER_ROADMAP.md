# Installer roadmap

Date: 2026-05-12

## Goal

Make ParserRIba installable for a non-technical Windows user without requiring
manual Python setup.

## Current recommended delivery

Keep using portable ZIP until Pyaterochka is stable with real RU proxies:

```text
dist\ParserRIba-windows-x64.zip
```

The ZIP already contains:

- `ParserRIba.exe`;
- `.env.example`;
- `README_START_HERE.txt`;
- `docs/`;
- `knowledge_base/`;
- optional copied `GeoLite2-City.mmdb` when present locally.

## Do not put into public installer

- real `.env`;
- proxy credentials;
- local logs;
- smoke HTML/PNG artifacts;
- virtual environments;
- private MaxMind keys.

## Installer candidate

Use Inno Setup first. It is simple, common for Windows desktop tools and good
enough for this project stage.

Planned installer behavior:

- install into `%LOCALAPPDATA%\ParserRIba` by default;
- create desktop shortcut;
- create Start Menu shortcut;
- open `README_START_HERE.txt` after install;
- keep user-editable `.env` near the executable;
- never overwrite an existing `.env` with proxy credentials;
- include `docs\WINDOWS_QUICKSTART.md`;
- include visual Pyaterochka helper script.

## Before building installer

1. Verify portable ZIP on a clean Windows machine.
2. Run:

```powershell
ParserRIba.exe --check-env
ParserRIba.exe --list-stores
```

3. Verify visual Pyaterochka mode with a working RU proxy.
4. Decide whether to include `GeoLite2-City.mmdb` in the installer or document
   separate download because of size/licensing.

## Future files

Recommended next implementation:

```text
installer\ParserRIba.iss
scripts\build_installer.ps1
```

Do this only after the portable ZIP is field-tested.
