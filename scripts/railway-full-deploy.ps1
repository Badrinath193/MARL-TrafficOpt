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

function Get-ExistingProject {
  param([string]$Name)
  $projects = Invoke-RailwayJson @("list", "--json")
  return $projects | Where-Object { $_.name -eq $Name } | Select-Object -First 1
}

function Ensure-ProjectLinked {
  param([string]$Name)
  try {
    $project = Invoke-RailwayJson @("init", "--name", $Name, "--json")
    Write-Host "Project ready."
    return $project
  } catch {
    $project = Get-ExistingProject $Name
    if (-not $project) {
      throw
    }
    Write-Host "Project already exists; linking local workspace instead of creating another project."
    & $RailwayCli link "--project" $project.id "--environment" $Environment | Out-Null
    if ($LASTEXITCODE -ne 0) {
      throw "Railway command failed: railway link --project $($project.id) --environment $Environment"
    }
    return $project
  }
}

function Ensure-Service {
  param($Project, [string]$Name)
  $existing = @($Project.services.edges | ForEach-Object { $_.node.name }) -contains $Name
  if ($existing) {
    Write-Host "Service already exists: $Name"
    return
  }
  Invoke-RailwayJson @("add", "--service", $Name, "--json") | Out-Null
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

function Get-ExistingServiceUrl {
  param([string]$Service)
  $status = & $RailwayCli status
  $line = $status | Where-Object { $_ -match "-\s+$([regex]::Escape($Service)):\s+.*https://[^\s]+" } | Select-Object -First 1
  if ($line -match "https://[^\s]+") {
    return $Matches[0]
  }
  return $null
}

function Ensure-PublicUrl {
  param([string]$Service, [string]$Port)
  $existingUrl = Get-ExistingServiceUrl $Service
  if ($existingUrl) {
    return $existingUrl
  }
  $domain = Invoke-RailwayJson @("domain", "--service", $Service, "--environment", $Environment, "--port", $Port, "--json")
  return Get-PublicUrl $domain
}

Write-Host "Checking Railway CLI..."
& $RailwayCli --version

Write-Host "Checking Railway authentication..."
& $RailwayCli whoami
if ($LASTEXITCODE -ne 0) {
  throw "Railway is not authenticated. Run railway login in a real terminal or set RAILWAY_TOKEN."
}

Write-Host "Creating or linking Railway project: $ProjectName"
$project = Ensure-ProjectLinked $ProjectName

Write-Host "Creating or reusing services..."
Ensure-Service $project "rl-service"
Ensure-Service $project "backend"
Ensure-Service $project "frontend"

Write-Host "Configuring RL/SUMO service variables..."
& $RailwayCli variable set "PORT=8000" "--service" "rl-service" "--environment" $Environment "--skip-deploys" "--json" | Out-Null
& $RailwayCli variable set "SUMO_HOME=/usr/share/sumo" "--service" "rl-service" "--environment" $Environment "--skip-deploys" "--json" | Out-Null

Write-Host "Deploying RL/SUMO service..."
& $RailwayCli up ".\rl-service" "--path-as-root" "--service" "rl-service" "--environment" $Environment "--detach"
if ($LASTEXITCODE -ne 0) { throw "RL/SUMO deploy failed." }
$rlUrl = Ensure-PublicUrl "rl-service" "8000"
Write-Host "RL/SUMO URL: $rlUrl"

Write-Host "Configuring backend variables..."
& $RailwayCli variable set "PORT=3001" "--service" "backend" "--environment" $Environment "--skip-deploys" "--json" | Out-Null
& $RailwayCli variable set "RL_SERVICE_URL=$rlUrl" "--service" "backend" "--environment" $Environment "--skip-deploys" "--json" | Out-Null

Write-Host "Deploying backend service..."
& $RailwayCli up ".\backend" "--path-as-root" "--service" "backend" "--environment" $Environment "--detach"
if ($LASTEXITCODE -ne 0) { throw "Backend deploy failed." }
$backendUrl = Ensure-PublicUrl "backend" "3001"
Write-Host "Backend URL: $backendUrl"

Write-Host "Configuring frontend variables..."
& $RailwayCli variable set "PORT=5173" "--service" "frontend" "--environment" $Environment "--skip-deploys" "--json" | Out-Null
& $RailwayCli variable set "VITE_BACKEND_URL=$backendUrl" "--service" "frontend" "--environment" $Environment "--skip-deploys" "--json" | Out-Null

Write-Host "Deploying frontend service..."
& $RailwayCli up ".\frontend" "--path-as-root" "--service" "frontend" "--environment" $Environment "--detach"
if ($LASTEXITCODE -ne 0) { throw "Frontend deploy failed." }
$frontendUrl = Ensure-PublicUrl "frontend" "5173"
Write-Host "Frontend URL: $frontendUrl"

Write-Host ""
Write-Host "Deployment submitted."
Write-Host "Check health after builds finish:"
Write-Host "  RL API:   $rlUrl/health"
Write-Host "  Backend:  $backendUrl/api/health"
Write-Host "  Frontend: $frontendUrl"
