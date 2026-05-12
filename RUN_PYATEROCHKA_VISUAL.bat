@echo off
setlocal
cd /d "%~dp0"
echo ParserRIba visual smoke: images enabled, browser stays open
echo.
echo If a captcha appears, solve it manually in the Camoufox window.
echo Close this console window when you are done inspecting the browser.
echo.
ParserRIba.exe --check-env
echo.
ParserRIba.exe --store pyaterochka --category "Рыба" --no-headless
echo.
pause
