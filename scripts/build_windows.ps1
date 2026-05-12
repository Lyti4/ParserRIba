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
    --collect-submodules "models" `
    --collect-submodules "parsers" `
    --collect-submodules "scripts" `
    --collect-submodules "utils" `
    --collect-data "apify_fingerprint_datapoints" `
    --collect-data "camoufox" `
    --collect-data "language_tags" `
    --hidden-import "geoip2" `
    --hidden-import "maxminddb" `
    --hidden-import "pydantic" `
    --add-data "knowledge_base;knowledge_base" `
    --add-data "config.yaml;." `
    main.py

$DistDir = "dist\ParserRIba"
Copy-Item -LiteralPath ".env.example" -Destination (Join-Path $DistDir ".env.example") -Force
Copy-Item -LiteralPath "README_START_HERE.txt" -Destination (Join-Path $DistDir "README_START_HERE.txt") -Force
Copy-Item -LiteralPath "RUN_PYATEROCHKA_VISUAL.bat" -Destination (Join-Path $DistDir "RUN_PYATEROCHKA_VISUAL.bat") -Force
Copy-Item -LiteralPath "SETUP_ENV.bat" -Destination (Join-Path $DistDir "SETUP_ENV.bat") -Force
if (Test-Path -LiteralPath (Join-Path $DistDir "docs")) {
    Remove-Item -LiteralPath (Join-Path $DistDir "docs") -Recurse -Force
}
Copy-Item -LiteralPath "docs" -Destination (Join-Path $DistDir "docs") -Recurse -Force

if (Test-Path -LiteralPath "GeoLite2-City.mmdb") {
    Copy-Item -LiteralPath "GeoLite2-City.mmdb" -Destination (Join-Path $DistDir "GeoLite2-City.mmdb") -Force
}

$ZipPath = "dist\ParserRIba-windows-x64.zip"
if (Test-Path -LiteralPath $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}
Compress-Archive -Path "$DistDir\*" -DestinationPath $ZipPath -Force

Write-Host ""
Write-Host "Build complete: dist\ParserRIba\ParserRIba.exe"
Write-Host "ZIP complete: $ZipPath"
Write-Host "Before publishing, test:"
Write-Host "  dist\ParserRIba\ParserRIba.exe --list-stores"
Write-Host "  dist\ParserRIba\ParserRIba.exe --check-env"
