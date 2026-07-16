# Local setup helper (PowerShell)

param(
  [switch]$SkipInfra,
  [switch]$SkipBackendInstall,
  [switch]$SkipFrontendInstall
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

if (-not $SkipInfra) {
  Write-Host "Starting Postgres + Redis..."
  docker compose -f (Join-Path $Root "infrastructure/docker-compose.yml") up -d
}

if (-not $SkipBackendInstall) {
  Push-Location (Join-Path $Root "backend")
  try {
    if (-not (Test-Path .venv)) {
      python -m venv .venv
    }
    & .\.venv\Scripts\python.exe -m pip install -U pip
    & .\.venv\Scripts\pip.exe install -e ".[dev]"
    if (-not (Test-Path .env)) {
      Copy-Item .env.example .env
    }
  } finally {
    Pop-Location
  }
}

if (-not $SkipFrontendInstall) {
  Push-Location (Join-Path $Root "frontend")
  try {
    if (-not (Test-Path .env.local)) {
      Copy-Item .env.example .env.local
    }
    npm ci
  } finally {
    Pop-Location
  }
}

Write-Host "Setup complete. See README.md for run commands."
