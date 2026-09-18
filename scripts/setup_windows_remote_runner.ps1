<#
.SYNOPSIS
  Prepare a Windows machine to act as a ParserRIba remote runner.

.DESCRIPTION
  This script is safe by default: it reports what is missing. If you run it as
  Administrator with -InstallOpenSSH and/or -OpenFirewall, it can enable the
  built-in Windows OpenSSH Server so Hermes/Codex can execute validation
  commands remotely while the human operator solves visual captchas locally.

.EXAMPLE
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_windows_remote_runner.ps1

.EXAMPLE
  # Run PowerShell as Administrator first:
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_windows_remote_runner.ps1 -InstallOpenSSH -OpenFirewall
#>

param(
    [string]$ProjectRoot = "C:\tmp\ParserRIba-clean",
    [string]$PythonExe = "C:\Python311\python.exe",
    [switch]$InstallOpenSSH,
    [switch]$OpenFirewall
)

$ErrorActionPreference = "Continue"

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "==== $Title ====" -ForegroundColor Cyan
}

function Test-IsAdmin {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
}

$isAdmin = Test-IsAdmin

Write-Section "ParserRIba Windows Remote Runner Setup"
Write-Host "Computer:    $env:COMPUTERNAME"
Write-Host "User:        $env:USERNAME"
Write-Host "Admin:       $isAdmin"
Write-Host "ProjectRoot: $ProjectRoot"
Write-Host "PythonExe:   $PythonExe"

Write-Section "Project checks"
if (Test-Path $ProjectRoot) {
    Write-Host "PASS: Project root exists" -ForegroundColor Green
} else {
    Write-Host "MISSING: Project root not found. Clone/copy ParserRIba to $ProjectRoot" -ForegroundColor Red
}

if (Test-Path $PythonExe) {
    & $PythonExe --version
} else {
    Write-Host "MISSING: Python not found at $PythonExe. Install Python 3.11." -ForegroundColor Red
}

if (Get-Command git -ErrorAction SilentlyContinue) {
    git --version
} else {
    Write-Host "MISSING: git is not in PATH." -ForegroundColor Yellow
}

Write-Section "OpenSSH Server"
$capability = Get-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 -ErrorAction SilentlyContinue
if ($capability) {
    Write-Host "OpenSSH capability state: $($capability.State)"
} else {
    Write-Host "Could not query OpenSSH capability. This Windows edition may not support it via WindowsCapability." -ForegroundColor Yellow
}

if ($InstallOpenSSH) {
    if (-not $isAdmin) {
        Write-Host "Cannot install OpenSSH without Administrator PowerShell." -ForegroundColor Red
    } elseif ($capability -and $capability.State -ne "Installed") {
        Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
    }
}

$service = Get-Service sshd -ErrorAction SilentlyContinue
if ($service) {
    Write-Host "sshd service: $($service.Status) / startup=$($service.StartType)"
    if ($InstallOpenSSH -and $isAdmin) {
        Set-Service -Name sshd -StartupType Automatic
        if ($service.Status -ne "Running") { Start-Service sshd }
        $service = Get-Service sshd
        Write-Host "sshd after setup: $($service.Status) / startup=$($service.StartType)" -ForegroundColor Green
    }
} else {
    Write-Host "sshd service not found. Run again as Administrator with -InstallOpenSSH." -ForegroundColor Yellow
}

if ($OpenFirewall) {
    if (-not $isAdmin) {
        Write-Host "Cannot open firewall without Administrator PowerShell." -ForegroundColor Red
    } else {
        $rule = Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue
        if (-not $rule) {
            New-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -DisplayName "OpenSSH Server (sshd)" -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
        } else {
            Enable-NetFirewallRule -Name "OpenSSH-Server-In-TCP"
        }
        Write-Host "Firewall rule OpenSSH-Server-In-TCP is enabled." -ForegroundColor Green
    }
}

Write-Section "Network info"
Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike "169.254*" -and $_.IPAddress -ne "127.0.0.1" } |
    Select-Object InterfaceAlias, IPAddress | Format-Table -AutoSize

Write-Section "Validation command"
Write-Host "After setup, run:"
Write-Host "powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_windows_validation.ps1 -SetupVenv -RunPytest -ZipArtifacts"
Write-Host ""
Write-Host "For real browser/captcha validation, run:"
Write-Host "powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_windows_validation.ps1 -RunVisualPyaterochka -ZipArtifacts"
