# Automatizacion de tests con modelo local (Windows / PowerShell).
# Equivalente al Makefile para entornos sin make.

[CmdletBinding()]
param(
    [string]$AnalystModel = "analyst-local-fast",
    [switch]$Up,
    [switch]$Down
)

$ErrorActionPreference = "Stop"

function Invoke-OllamaUp {
    Write-Host ">> levantando ollama..."
    docker compose up -d ollama
    Write-Host ">> esperando a que ollama-init descargue los modelos (primera vez tarda)..."
    docker compose up ollama-init
    Write-Host ">> modelos listos"
}

function Invoke-StackUp {
    docker compose up -d postgres analytics redis
    Write-Host ">> esperando DBs..."
    Start-Sleep -Seconds 5
}

if ($Up) {
    Invoke-OllamaUp
    Invoke-StackUp
}

$env:ANALYST_MODEL = $AnalystModel
$env:RUN_AGENT = "1"

Write-Host ">> corriendo pytest con ANALYST_MODEL=$AnalystModel ..."
py -m pytest tests -q

if ($Down) {
    Write-Host ">> bajando stack temporal..."
    docker compose down
}