$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    Write-Host 'Run py -3.11 iniciar.py first to prepare the environment.'
    exit 1
}
& $pythonPath iniciar.py
