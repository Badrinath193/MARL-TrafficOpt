param(
  [string]$RailwayCli = "railway"
)

$ErrorActionPreference = "Stop"

Write-Host "Checking Railway CLI..."
& $RailwayCli --version

Write-Host "Checking Railway authentication..."
try {
  & $RailwayCli whoami
} catch {
  Write-Host ""
  Write-Host "Railway CLI is not logged in."
  Write-Host "Run: railway login"
  Write-Host "Then create three Railway services from GitHub using root directories:"
  Write-Host "  rl-service"
  Write-Host "  backend"
  Write-Host "  frontend"
  exit 1
}

Write-Host ""
Write-Host "Railway CLI is ready."
Write-Host "Use the Railway dashboard to create three GitHub-backed services from this repo:"
Write-Host "  1. rl-service  -> root directory rl-service"
Write-Host "  2. backend     -> root directory backend"
Write-Host "  3. frontend    -> root directory frontend"
Write-Host ""
Write-Host "Set the environment variables documented in docs/deployment.md."
