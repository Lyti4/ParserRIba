param(
    [string]$Python = "C:\Python311\python.exe",
    [string]$BuildVenv = ".build-venv",
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

function Invoke-NativeChecked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [Parameter(Mandatory = $true)]
        [string]$Step,
        [Parameter(Mandatory = $true)]
        [string[]]$ArgumentList
    )

    & $FilePath @ArgumentList
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "$Step failed with native exit code $exitCode."
    }
}

function Get-VirtualKeyboardRuntimeFiles {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    if (-not (Test-Path -LiteralPath $Root)) {
        throw "Runtime root not found: $Root"
    }

    return @(
        Get-ChildItem -LiteralPath $Root -Recurse -File |
            Where-Object {
                $_.Extension -in ".dll", ".pyd" -and
                    $_.Name -match "(?i)virtualkeyboard"
            }
    )
}

function Assert-RequiredQtRuntimeAssets {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DistDir
    )

    $requiredPaths = @(
        "_internal\PySide6\Qt6Core.dll",
        "_internal\PySide6\Qt6Gui.dll",
        "_internal\PySide6\Qt6Widgets.dll",
        "_internal\PySide6\plugins\platforms\qwindows.dll"
    )
    foreach ($relativePath in $requiredPaths) {
        if (-not (Test-Path -LiteralPath (Join-Path $DistDir $relativePath))) {
            throw "Required Qt runtime asset is missing: $relativePath"
        }
    }
}

function Assert-NoVirtualKeyboardRuntime {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    $remaining = @(Get-VirtualKeyboardRuntimeFiles -Root $Root)
    if ($remaining.Count -gt 0) {
        $paths = $remaining.FullName -join "; "
        throw "Forbidden Virtual Keyboard runtime binaries remain: $paths"
    }
}

function Remove-OptionalVirtualKeyboardRuntime {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DistDir
    )

    $knownOptionalPaths = @(
        "_internal\PySide6\Qt6VirtualKeyboard.dll",
        "_internal\PySide6\plugins\platforminputcontexts\qtvirtualkeyboardplugin.dll"
    )
    foreach ($relativePath in $knownOptionalPaths) {
        $runtimePath = Join-Path $DistDir $relativePath
        if (Test-Path -LiteralPath $runtimePath) {
            Remove-Item -LiteralPath $runtimePath -Force
        }
    }

    Assert-RequiredQtRuntimeAssets -DistDir $DistDir
    Assert-NoVirtualKeyboardRuntime -Root $DistDir
}

function Assert-NoVirtualKeyboardArchiveRuntime {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ZipPath
    )

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        $remaining = @(
            $archive.Entries | Where-Object {
                $entryName = [System.IO.Path]::GetFileName($_.FullName)
                [System.IO.Path]::GetExtension($entryName) -in ".dll", ".pyd" -and
                    $entryName -match "(?i)virtualkeyboard"
            }
        )
        if ($remaining.Count -gt 0) {
            $paths = $remaining.FullName -join "; "
            throw "Forbidden Virtual Keyboard runtime binaries remain in archive: $paths"
        }
    } finally {
        $archive.Dispose()
    }
}

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
    Invoke-NativeChecked -FilePath $Python -ArgumentList @("-m", "venv", $BuildVenv) -Step "Create build virtual environment"
}

$BuildPython = Join-Path $BuildVenv "Scripts\python.exe"

Invoke-NativeChecked -FilePath $BuildPython -ArgumentList @("-m", "pip", "install", "--upgrade", "pip") -Step "Upgrade build pip"
Invoke-NativeChecked -FilePath $BuildPython -ArgumentList @("-m", "pip", "install", "-r", "requirements.txt") -Step "Install runtime requirements"
Invoke-NativeChecked -FilePath $BuildPython -ArgumentList @("-m", "pip", "install", "-r", "requirements-build.txt") -Step "Install build requirements"
Invoke-NativeChecked -FilePath $BuildPython -ArgumentList @("-c", "import PySide6") -Step "Verify PySide6 build dependency"

$PyInstallerArguments = @(
    "-m",
    "PyInstaller",
    "--name", "ParserRIba",
    "--onedir",
    "--console",
    "--collect-submodules", "models",
    "--collect-submodules", "scripts",
    "--collect-submodules", "utils",
    "--collect-data", "apify_fingerprint_datapoints",
    "--collect-data", "camoufox",
    "--collect-data", "language_tags",
    "--hidden-import", "geoip2",
    "--hidden-import", "maxminddb",
    "--hidden-import", "pydantic",
    "--hidden-import", "PySide6.QtCore",
    "--hidden-import", "PySide6.QtGui",
    "--hidden-import", "PySide6.QtWidgets",
    "--recursive-copy-metadata", "PySide6",
    "--add-data", "knowledge_base;knowledge_base",
    "--add-data", "config.yaml;.",
    "scripts\run_desktop_launcher.py"
)
Invoke-NativeChecked -FilePath $BuildPython -ArgumentList $PyInstallerArguments -Step "Build ParserRIba portable launcher"

$DistDir = "dist\ParserRIba"
Remove-OptionalVirtualKeyboardRuntime -DistDir $DistDir
Copy-Item -LiteralPath ".env.example" -Destination (Join-Path $DistDir ".env.example") -Force
Copy-Item -LiteralPath "README_START_HERE.txt" -Destination (Join-Path $DistDir "README_START_HERE.txt") -Force
Copy-Item -LiteralPath "RUN_PYATEROCHKA_VISUAL.bat" -Destination (Join-Path $DistDir "RUN_PYATEROCHKA_VISUAL.bat") -Force
Copy-Item -LiteralPath "SETUP_ENV.bat" -Destination (Join-Path $DistDir "SETUP_ENV.bat") -Force
Copy-Item -LiteralPath "OPEN_REPORTS.bat" -Destination (Join-Path $DistDir "OPEN_REPORTS.bat") -Force
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
Assert-NoVirtualKeyboardArchiveRuntime -ZipPath $ZipPath
$ChecksumPath = "$ZipPath.sha256"
$Hash = Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256
"$($Hash.Hash)  $(Split-Path -Leaf $ZipPath)" | Set-Content -LiteralPath $ChecksumPath -Encoding ascii

Write-Host ""
Write-Host "Build complete: dist\ParserRIba\ParserRIba.exe"
Write-Host "ZIP complete: $ZipPath"
Write-Host "SHA256 complete: $ChecksumPath"
Write-Host "Before publishing, test:"
Write-Host "  dist\ParserRIba\ParserRIba.exe --smoke"
