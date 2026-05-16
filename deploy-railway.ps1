$ErrorActionPreference = "Stop"

$RailwayCli = "C:\Users\tshiv\AppData\Roaming\npm\railway.cmd"
if (-not (Test-Path $RailwayCli)) {
  $RailwayCli = "railway"
}

Write-Host "Deploying MARL TrafficOpt to Railway..."
Write-Host "Using Railway CLI: $RailwayCli"

.\scripts\railway-full-deploy.ps1 -RailwayCli $RailwayCli -ProjectName "MARL-TrafficOpt"
