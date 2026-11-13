$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    Write-Host 'Primeiro siga a instalação no README.md para criar o ambiente .venv.'
    exit 1
}
& $pythonPath iniciar.py
