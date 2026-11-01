# PowerShell entry point; no execution-policy or machine configuration changes.
param([Parameter(Mandatory=$true)][ValidateSet("rust","go","cpp","python")][string]$Language,
      [Parameter(ValueFromRemainingArguments=$true)][string[]]$ExampleArguments)
$ErrorActionPreference = "Stop"
& python (Join-Path $PSScriptRoot "scripts/run-example.py") $Language @ExampleArguments
exit $LASTEXITCODE
