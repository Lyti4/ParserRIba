<#
.SYNOPSIS
  ParserRIba Windows validation and artifact collection runner.

.DESCRIPTION
  Run this from the Windows working copy (normally C:\tmp\ParserRIba-clean).
  It runs the local validation gate, captures logs, and optionally starts the
  manual Pyaterochka visual flow where the operator solves captcha in Camoufox.

  Generated logs/artifacts are written under logs/windows_runner/ and are not
  committed.

.EXAMPLE
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_windows_validation.ps1

.EXAMPLE
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_windows_validation.ps1 -RunPytest -RunVisualPyaterochka
#>

param(
    [string]$ProjectRoot = "C:\tmp\ParserRIba-clean",
    [string]$PythonExe = "C:\Python311\python.exe",
    [switch]$SetupVenv,
    [switch]$RunPytest,
    [switch]$RunVisualPyaterochka,
    [switch]$SkipLauncherSmoke,
    [switch]$ZipArtifacts
)

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

function New-RunDirectory {
    param([string]$Root)
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $dir = Join-Path $Root "logs\windows_runner\$stamp"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    return $dir
}

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "==== $Title ====" -ForegroundColor Cyan
}

function Invoke-LoggedCommand {
    param(
        [string]$Name,
        [string]$Command,
        [string]$LogDir,
        [switch]$AllowFailure
    )

    Write-Section $Name
    $logPath = Join-Path $LogDir ("$Name.log" -replace '[^A-Za-z0-9_.-]', '_')
    $exitPath = Join-Path $LogDir ("$Name.exit" -replace '[^A-Za-z0-9_.-]', '_')
    Write-Host "Command: $Command"
    Write-Host "Log: $logPath"

    $start = Get-Date
    cmd.exe /c "$Command" *> $logPath
    $code = $LASTEXITCODE
    $elapsed = [int]((Get-Date) - $start).TotalSeconds
    "exit_code=$code`nelapsed_seconds=$elapsed`ncommand=$Command" | Set-Content -Encoding UTF8 $exitPath

    if ($code -eq 0) {
        Write-Host "PASS: $Name ($elapsed s)" -ForegroundColor Green
    } else {
        Write-Host "FAIL: $Name exit=$code ($elapsed s)" -ForegroundColor Red
        if (-not $AllowFailure) {
            throw "Step failed: $Name. See $logPath"
        }
    }
    return $code
}

function Copy-IfExists {
    param([string]$Path, [string]$Destination)
    if (Test-Path $Path) {
        New-Item -ItemType Directory -Force -Path $Destination | Out-Null
        Copy-Item -Path $Path -Destination $Destination -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Set-Location $ProjectRoot
$runDir = New-RunDirectory -Root $ProjectRoot
$summaryPath = Join-Path $runDir "SUMMARY.md"

Write-Section "ParserRIba Windows Runner"
Write-Host "ProjectRoot: $ProjectRoot"
Write-Host "RunDir:      $runDir"
Write-Host "Computer:    $env:COMPUTERNAME"
Write-Host "User:        $env:USERNAME"
Write-Host "Date:        $(Get-Date -Format o)"

$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

try {
    if ($SetupVenv -or -not (Test-Path $venvPython)) {
        Write-Section "Setup virtualenv"
        if (-not (Test-Path $PythonExe)) {
            throw "Python not found at $PythonExe. Install Python 3.11 or pass -PythonExe."
        }
        Invoke-LoggedCommand -Name "setup_venv_create" -Command "`"$PythonExe`" -m venv .venv" -LogDir $runDir | Out-Null
        Invoke-LoggedCommand -Name "setup_pip_upgrade" -Command "`"$venvPython`" -m pip install --upgrade pip" -LogDir $runDir | Out-Null
        Invoke-LoggedCommand -Name "setup_requirements" -Command "`"$venvPython`" -m pip install -r requirements.txt" -LogDir $runDir | Out-Null
    }

    if (-not (Test-Path $venvPython)) {
        throw "Virtualenv python not found at $venvPython. Re-run with -SetupVenv."
    }

    Invoke-LoggedCommand -Name "python_version" -Command "`"$venvPython`" --version" -LogDir $runDir | Out-Null
    Invoke-LoggedCommand -Name "check_environment" -Command "`"$venvPython`" scripts\check_environment.py" -LogDir $runDir -AllowFailure | Out-Null
    Invoke-LoggedCommand -Name "compileall" -Command "`"$venvPython`" -m compileall -q models utils scripts tests stores launcher" -LogDir $runDir | Out-Null
    Invoke-LoggedCommand -Name "architecture_check" -Command "`"$venvPython`" scripts\architecture_check.py" -LogDir $runDir | Out-Null
    Invoke-LoggedCommand -Name "agent_ops_check" -Command "`"$venvPython`" scripts\agent_ops_check.py --scope all" -LogDir $runDir | Out-Null

    if (-not $SkipLauncherSmoke) {
        Invoke-LoggedCommand -Name "launcher_smoke" -Command "`"$venvPython`" scripts\run_desktop_launcher.py --smoke" -LogDir $runDir | Out-Null
    }

    if ($RunPytest) {
        Invoke-LoggedCommand -Name "pytest_full" -Command "`"$venvPython`" -m pytest -q" -LogDir $runDir -AllowFailure | Out-Null
    }

    if ($RunVisualPyaterochka) {
        Write-Section "Manual Pyaterochka visual flow"
        Write-Host "Camoufox may open. If captcha/challenge appears, solve it manually."
        Write-Host "When product/catalog content is visible, return to PowerShell and follow the script prompt."
        Invoke-LoggedCommand -Name "pyaterochka_visual" -Command "powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_pyaterochka_visual.ps1" -LogDir $runDir -AllowFailure | Out-Null
    }

    Write-Section "Collect artifacts"
    $artifactDir = Join-Path $runDir "artifacts"
    New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
    Copy-IfExists -Path (Join-Path $ProjectRoot "data") -Destination $artifactDir
    Copy-IfExists -Path (Join-Path $ProjectRoot "logs\agent_utf8") -Destination $artifactDir
    Copy-IfExists -Path (Join-Path $ProjectRoot "graphify-out\GRAPH_REPORT.md") -Destination $artifactDir

    $status = "PASS"
} catch {
    $status = "FAIL"
    $errorMessage = $_.Exception.Message
    Write-Host "VALIDATION FAILED: $errorMessage" -ForegroundColor Red
} finally {
    $gitStatus = ""
    if (Get-Command git -ErrorAction SilentlyContinue) {
        $gitStatus = git status --short --branch 2>$null | Out-String
    }

    $summary = @"
# ParserRIba Windows Validation Summary

- Status: $status
- Timestamp: $(Get-Date -Format o)
- Machine: $env:COMPUTERNAME
- User: $env:USERNAME
- ProjectRoot: $ProjectRoot
- RunDir: $runDir
- Python: $venvPython
- RunPytest: $RunPytest
- RunVisualPyaterochka: $RunVisualPyaterochka

## Git Status

```text
$gitStatus
```

## Logs

Each command wrote a `.log` and `.exit` file in this directory.

## Operator Notes

If the visual Pyaterochka flow was run, describe here:

- Did Camoufox open?
- Was captcha shown?
- Was captcha solved manually?
- Did catalog/product cards become visible?
- Which artifact files were produced under `data/`?
"@
    $summary | Set-Content -Encoding UTF8 $summaryPath

    if ($ZipArtifacts) {
        $zipPath = "$runDir.zip"
        if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
        Compress-Archive -Path $runDir -DestinationPath $zipPath -Force
        Write-Host "ZIP: $zipPath" -ForegroundColor Yellow
    }

    Write-Section "Done"
    Write-Host "Summary: $summaryPath"
    Write-Host "Status:  $status"
    if ($status -ne "PASS") { exit 1 }
}
