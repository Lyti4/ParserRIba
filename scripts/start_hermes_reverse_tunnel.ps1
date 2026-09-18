<#
.SYNOPSIS
  Start a reverse SSH tunnel from the Windows operator machine to Hermes VPS.

.DESCRIPTION
  Run this on Windows. It lets Hermes connect back to this Windows machine via:

      ssh parserriba-windows

  The tunnel is:

      Hermes VPS 127.0.0.1:2222 -> Windows 127.0.0.1:22

  The script also installs Hermes' public key into the Windows OpenSSH
  authorized_keys location for the current user. If run as Administrator, it can
  also install OpenSSH Server and enable the firewall rule.

.EXAMPLE
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_hermes_reverse_tunnel.ps1

.EXAMPLE
  # Run PowerShell as Administrator for first setup:
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_hermes_reverse_tunnel.ps1 -InstallOpenSSH -OpenFirewall
#>

param(
    [string]$HermesHost = "132.243.115.14",
    [string]$HermesUser = "hermesadmin",
    [int]$RemotePort = 2222,
    [switch]$InstallOpenSSH,
    [switch]$OpenFirewall,
    [switch]$Background
)

$ErrorActionPreference = "Stop"

$HermesToWindowsPublicKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJMBnBT3rZlSj44iPL82dqYlMtZYw/srycTzD0mUqAX3 parserriba-hermes-to-windows-2026-06-16"

function Test-IsAdmin {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
}

function Add-KeyIfMissing {
    param([string]$Path, [string]$Key)
    $dir = Split-Path $Path -Parent
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    if (-not (Test-Path $Path)) {
        New-Item -ItemType File -Force -Path $Path | Out-Null
    }
    $content = Get-Content -Raw -ErrorAction SilentlyContinue $Path
    if ($content -notlike "*$Key*") {
        Add-Content -Encoding ascii -Path $Path -Value $Key
        Write-Host "Added Hermes public key to $Path" -ForegroundColor Green
    } else {
        Write-Host "Hermes public key already present in $Path" -ForegroundColor Green
    }
}

$isAdmin = Test-IsAdmin
Write-Host "Windows user: $env:USERNAME"
Write-Host "Admin: $isAdmin"
Write-Host "Hermes VPS: $HermesUser@$HermesHost"
Write-Host "Reverse port: $RemotePort"

if ($InstallOpenSSH) {
    if (-not $isAdmin) {
        Write-Warning "-InstallOpenSSH requires Administrator PowerShell. Skipping install."
    } else {
        $cap = Get-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 -ErrorAction SilentlyContinue
        if ($cap -and $cap.State -ne "Installed") {
            Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 | Out-Null
        }
    }
}

$service = Get-Service sshd -ErrorAction SilentlyContinue
if ($service) {
    if ($isAdmin) {
        Set-Service -Name sshd -StartupType Automatic
        if ($service.Status -ne "Running") { Start-Service sshd }
        Write-Host "sshd service running" -ForegroundColor Green
    } else {
        Write-Host "sshd service exists: $($service.Status). If not running, run this script as Administrator with -InstallOpenSSH." -ForegroundColor Yellow
    }
} else {
    Write-Warning "sshd service not found. Run as Administrator with -InstallOpenSSH."
}

if ($OpenFirewall) {
    if (-not $isAdmin) {
        Write-Warning "-OpenFirewall requires Administrator PowerShell. Skipping firewall."
    } else {
        $rule = Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue
        if (-not $rule) {
            New-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -DisplayName "OpenSSH Server (sshd)" -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
        } else {
            Enable-NetFirewallRule -Name "OpenSSH-Server-In-TCP" | Out-Null
        }
        Write-Host "OpenSSH firewall rule enabled" -ForegroundColor Green
    }
}

# User key; useful for non-admin users and some Windows OpenSSH configs.
$userAuthorizedKeys = Join-Path $env:USERPROFILE ".ssh\authorized_keys"
Add-KeyIfMissing -Path $userAuthorizedKeys -Key $HermesToWindowsPublicKey

# Admin key; default Windows OpenSSH often requires this for administrators.
if ($isAdmin) {
    $adminAuthorizedKeys = "$env:ProgramData\ssh\administrators_authorized_keys"
    Add-KeyIfMissing -Path $adminAuthorizedKeys -Key $HermesToWindowsPublicKey
    icacls.exe $adminAuthorizedKeys /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F" | Out-Null
}

$sshExe = Get-Command ssh.exe -ErrorAction SilentlyContinue
if (-not $sshExe) {
    throw "ssh.exe not found in PATH. Install Windows OpenSSH Client."
}

Write-Host "Testing outbound SSH to Hermes..." -ForegroundColor Cyan
ssh.exe -o BatchMode=no -o ConnectTimeout=15 "$HermesUser@$HermesHost" "echo hermes-vps-ok"
if ($LASTEXITCODE -ne 0) {
    throw "Could not SSH to Hermes VPS. Confirm the existing VPS key/auth still works from this Windows machine."
}

$sshArgs = @(
    "-NT",
    "-o", "ExitOnForwardFailure=yes",
    "-o", "ServerAliveInterval=30",
    "-o", "ServerAliveCountMax=3",
    "-R", "127.0.0.1:$RemotePort`:127.0.0.1:22",
    "$HermesUser@$HermesHost"
)

Write-Host "Starting reverse tunnel:" -ForegroundColor Cyan
Write-Host "ssh.exe $($sshArgs -join ' ')"
Write-Host "Keep this PowerShell window open. Hermes can then run: ssh parserriba-windows" -ForegroundColor Yellow

if ($Background) {
    Start-Process -FilePath $sshExe.Source -ArgumentList $sshArgs -WindowStyle Minimized
    Write-Host "Reverse tunnel started in a minimized ssh.exe process." -ForegroundColor Green
} else {
    & $sshExe.Source @sshArgs
}
