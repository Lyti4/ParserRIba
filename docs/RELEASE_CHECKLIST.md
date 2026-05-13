# Release checklist

Date: 2026-05-12

Use this before publishing `ParserRIba-windows-x64.zip` to GitHub Releases.

## Local build

- [ ] Working tree is clean.
- [ ] Tests pass:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

- [ ] Portable build succeeds:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1 -Clean
```

- [ ] ZIP and checksum exist:

```text
dist\ParserRIba-windows-x64.zip
dist\ParserRIba-windows-x64.zip.sha256
```

## Runtime checks

- [ ] `ParserRIba.exe --check-env` passes.
- [ ] `ParserRIba.exe --list-stores` works.
- [ ] `SETUP_ENV.bat` creates `.env` only when it does not exist.
- [ ] `RUN_PYATEROCHKA_VISUAL.bat` opens visible Camoufox.
- [ ] `OPEN_REPORTS.bat` opens generated reports.

## Pyaterochka field check

- [ ] `.env` contains working RU proxy or proxy pool.
- [ ] `PARSER_GEOIP=1` when `GeoLite2-City.mmdb` is present.
- [ ] Visual mode loads captcha images.
- [ ] Visual mode waits until product cards are visible before saving the final manual report.
- [ ] Smoke report includes:
  - final URL;
  - HTTP status;
  - block reason;
  - browser external IP;
  - proxy mask;
  - network status counts;
  - catalog/API response samples;
  - screenshot path.

## Privacy and secrets

- [ ] `.env` is not inside the ZIP.
- [ ] Real proxy strings are not committed.
- [ ] Logs are not committed.
- [ ] Smoke HTML/PNG/JSON artifacts are not committed.
- [ ] MaxMind keys are not committed.

## Release notes

Mention:

- this is a first portable test build;
- Camoufox browser must be available locally unless bundled later;
- RU proxy is recommended for Pyaterochka;
- captcha is handled manually in visual mode;
- no paid/cloud captcha solver is included.

## Installer gate

Do not build a public installer until:

- [ ] portable ZIP is tested on a clean Windows machine;
- [ ] Pyaterochka behavior with RU proxy is documented;
- [ ] decision is made about bundling or separately installing Camoufox;
- [ ] decision is made about bundling or separately downloading GeoIP.
