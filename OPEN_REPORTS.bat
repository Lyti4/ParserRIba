@echo off
setlocal
cd /d "%~dp0"

if not exist "data" (
    echo The data folder does not exist yet.
    echo Run Pyaterochka smoke or visual check first.
    pause
    exit /b 0
)

start "" "data"

if exist "data\pyaterochka_camoufox_smoke.md" (
    start "" "data\pyaterochka_camoufox_smoke.md"
)

if exist "data\pyaterochka_camoufox_smoke.png" (
    start "" "data\pyaterochka_camoufox_smoke.png"
)

if exist "data\pyaterochka_camoufox_smoke.html" (
    echo HTML snapshot: data\pyaterochka_camoufox_smoke.html
)

echo Reports opened when available.
pause
