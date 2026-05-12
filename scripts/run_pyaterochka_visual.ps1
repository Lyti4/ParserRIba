param(
    [string]$Category = "Рыба",
    [int]$Attempts = 1
)

$ErrorActionPreference = "Stop"

Write-Host "ParserRIba visual smoke: images enabled, browser stays open"
Write-Host "Category: $Category"
Write-Host "Attempts: $Attempts"
Write-Host ""
Write-Host "If a captcha appears, solve it manually in the Camoufox window."
Write-Host "Close this PowerShell window when you are done inspecting the browser."
Write-Host ""

.\.venv\Scripts\python.exe scripts\smoke_pyaterochka_camoufox.py `
    --category $Category `
    --attempts $Attempts `
    --no-headless `
    --load-images `
    --pause
