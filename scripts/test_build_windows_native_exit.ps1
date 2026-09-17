<#
.SYNOPSIS
  Regression test for native command failure handling in build_windows.ps1.

.DESCRIPTION
  Extracts and loads only Invoke-NativeChecked through the PowerShell AST.
  It never executes the build script body. cmd.exe supplies deterministic native
  success and nonzero child exit codes.
#>

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$buildScript = Join-Path $projectRoot "scripts\build_windows.ps1"

function Assert-Condition {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $buildScript,
    [ref]$tokens,
    [ref]$parseErrors
)
Assert-Condition -Condition ($parseErrors.Count -eq 0) -Message "build_windows.ps1 has PowerShell parse errors."

$helper = $ast.Find(
    {
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $node.Name -eq "Invoke-NativeChecked"
    },
    $true
)
Assert-Condition -Condition ($null -ne $helper) -Message "Invoke-NativeChecked was not found in build_windows.ps1."

. ([scriptblock]::Create($helper.Extent.Text))

$cmd = $env:ComSpec
Assert-Condition -Condition (-not [string]::IsNullOrWhiteSpace($cmd)) -Message "COMSPEC is required for the native child-process test."

$firstSuccessReached = $false
Invoke-NativeChecked -FilePath $cmd -ArgumentList @("/d", "/c", "exit 0") -Step "first native success"
$firstSuccessReached = $true
Assert-Condition -Condition $firstSuccessReached -Message "A successful native command did not return to the caller."

$failedCallCaught = $false
$afterFailedCallReached = $false
try {
    Invoke-NativeChecked -FilePath $cmd -ArgumentList @("/d", "/c", "exit 29") -Step "expected native failure"
    $afterFailedCallReached = $true
} catch {
    $failedCallCaught = $_.Exception.Message -match "expected native failure" -and $_.Exception.Message -match "29"
}
Assert-Condition -Condition $failedCallCaught -Message "A native nonzero exit was not reported with its step and exit code."
Assert-Condition -Condition (-not $afterFailedCallReached) -Message "Execution continued after a failing native invocation."

$successAfterFailureReached = $false
Invoke-NativeChecked -FilePath $cmd -ArgumentList @("/d", "/c", "exit 0") -Step "native success after handled failure"
$successAfterFailureReached = $true
Assert-Condition -Condition $successAfterFailureReached -Message "A later native success did not run after the expected failure was handled."
Assert-Condition -Condition ($LASTEXITCODE -eq 0) -Message "Expected child failure leaked into the successful harness exit state."

Write-Output "PASS: Invoke-NativeChecked handles native success, nonzero exit and later success."
exit 0
