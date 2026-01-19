# Start backend script: activates venv and runs uvicorn with correct module path
param(
    [switch]$Reload
)

Set-Location -Path $PSScriptRoot
if (Test-Path '.\.venv\Scripts\Activate.ps1') {
    & .\.venv\Scripts\Activate.ps1
} elseif (Test-Path '..\.venv\Scripts\Activate.ps1') {
    & ..\.venv\Scripts\Activate.ps1
}

$py = if (Test-Path '.\.venv\Scripts\python.exe') { '.\.venv\Scripts\python.exe' } elseif (Test-Path '..\.venv\Scripts\python.exe') { '..\.venv\Scripts\python.exe' } else { 'python' }
if ($Reload) {
    & $py -m uvicorn backend.agent_init:app --host 127.0.0.1 --port 65252 --reload
} else {
    & $py -m uvicorn backend.agent_init:app --host 127.0.0.1 --port 65252
}
