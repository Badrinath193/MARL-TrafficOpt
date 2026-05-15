param(
  [string]$RailwayCli = "railway",
  [string]$ProjectName = "MARL-TrafficOpt",
  [string]$Environment = "production"
)

$ErrorActionPreference = "Stop"

function Invoke-RailwayJson {
  param([string[]]$ArgsList)
  $output = & $RailwayCli @ArgsList
  if ($LASTEXITCODE -ne 0) {
    throw "Railway command failed: railway $($ArgsList -join ' ')"
  }
  if (-not $output) {
    return $null
  }
  return $output | ConvertFrom-Json
}

function Get-PublicUrl {
  param($DomainResult)
  if ($DomainResult.url) { return $DomainResult.url }
  if ($DomainResult.domain) { return "https://$($DomainResult.domain)" }
  if ($DomainResult.host) { return "https://$($DomainResult.host)" }
  if ($DomainResult.name) { return "https://$($DomainResult.name)" }
  $text = $DomainResult | ConvertTo-Json -Compress
  if ($text -match "https://[^`"'\s,}]+") { return $Matches[0] }
  throw "Could not parse Railway public URL from: $text"
}

Write-Host "Checking Railway CLI..."
& $RailwayCli --version

Write-Host "Checking Railway authentication..."
& $RailwayCli whoami
if ($LASTEXITCODE -ne 0) {
  throw "Railway is not authenticated. Run railway login in a real terminal or set RAILWAY_TOKEN."
}

Write-Host "Creating or linking Railway project: $ProjectName"
$project = Invoke-RailwayJson @("init", "--name", $ProjectName, "--json")
Write-Host "Project ready."

Write-Host "Creating services..."
Invoke-RailwayJson @("add", "--service", "rl-service", "--json") | Out-Null
Invoke-RailwayJson @("add", "--service", "backend", "--json") | Out-Null
Invoke-RailwayJson @("add", "--service", "frontend", "--json") | Out-Null

Write-Host "Configuring RL/SUMO service variables..."
& $RailwayCli variable set "PORT=8000" "--service" "rl-service" "--environment" $Environment "--skip-deploys" "--json" | Out-Null
& $RailwayCli variable set "SUMO_HOME=/usr/share/sumo" "--service" "rl-service" "--environment" $Environment "--skip-deploys" "--json" | Out-Null

Write-Host "Deploying RL/SUMO service..."
& $RailwayCli up ".\rl-service" "--path-as-root" "--service" "rl-service" "--environment" $Environment "--detach"
if ($LASTEXITCODE -ne 0) { throw "RL/SUMO deploy failed." }
$rlDomain = Invoke-RailwayJson @("domain", "--service", "rl-service", "--environment", $Environment, "--port", "8000", "--json")
$rlUrl = Get-PublicUrl $rlDomain
Write-Host "RL/SUMO URL: $rlUrl"

Write-Host "Configuring backend variables..."
& $RailwayCli variable set "PORT=3001" "--service" "backend" "--environment" $Environment "--skip-deploys" "--json" | Out-Null
& $RailwayCli variable set "RL_SERVICE_URL=$rlUrl" "--service" "backend" "--environment" $Environment "--skip-deploys" "--json" | Out-Null

Write-Host "Deploying backend service..."
& $RailwayCli up ".\backend" "--path-as-root" "--service" "backend" "--environment" $Environment "--detach"
if ($LASTEXITCODE -ne 0) { throw "Backend deploy failed." }
$backendDomain = Invoke-RailwayJson @("domain", "--service", "backend", "--environment", $Environment, "--port", "3001", "--json")
$backendUrl = Get-PublicUrl $backendDomain
Write-Host "Backend URL: $backendUrl"

Write-Host "Configuring frontend variables..."
& $RailwayCli variable set "PORT=5173" "--service" "frontend" "--environment" $Environment "--skip-deploys" "--json" | Out-Null
& $RailwayCli variable set "VITE_BACKEND_URL=$backendUrl" "--service" "frontend" "--environment" $Environment "--skip-deploys" "--json" | Out-Null

Write-Host "Deploying frontend service..."
& $RailwayCli up ".\frontend" "--path-as-root" "--service" "frontend" "--environment" $Environment "--detach"
if ($LASTEXITCODE -ne 0) { throw "Frontend deploy failed." }
$frontendDomain = Invoke-RailwayJson @("domain", "--service", "frontend", "--environment", $Environment, "--port", "5173", "--json")
$frontendUrl = Get-PublicUrl $frontendDomain
Write-Host "Frontend URL: $frontendUrl"

Write-Host ""
Write-Host "Deployment submitted."
Write-Host "Check health after builds finish:"
Write-Host "  RL API:   $rlUrl/health"
Write-Host "  Backend:  $backendUrl/api/health"
Write-Host "  Frontend: $frontendUrl"
