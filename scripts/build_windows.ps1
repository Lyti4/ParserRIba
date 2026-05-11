param(
    [string]$Python = "C:\Python311\python.exe",
    [string]$BuildVenv = ".build-venv",
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python not found: $Python"
}

if ($Clean -and (Test-Path -LiteralPath "build")) {
    Remove-Item -LiteralPath "build" -Recurse -Force
}

if ($Clean -and (Test-Path -LiteralPath "dist")) {
    Remove-Item -LiteralPath "dist" -Recurse -Force
}

if (-not (Test-Path -LiteralPath $BuildVenv)) {
    & $Python -m venv $BuildVenv
}

$BuildPython = Join-Path $BuildVenv "Scripts\python.exe"

& $BuildPython -m pip install --upgrade pip
& $BuildPython -m pip install -r requirements.txt
& $BuildPython -m pip install -r requirements-build.txt

& $BuildPython -m PyInstaller `
    --name ParserRIba `
    --onedir `
    --console `
    --add-data "knowledge_base;knowledge_base" `
    --add-data "config.yaml;." `
    main.py

Write-Host ""
Write-Host "Build complete: dist\ParserRIba\ParserRIba.exe"
Write-Host "Before publishing, test:"
Write-Host "  dist\ParserRIba\ParserRIba.exe --list-stores"
