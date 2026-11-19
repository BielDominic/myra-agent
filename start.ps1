# Native MYRA launcher. Open WebUI and Docker are not required.
$ErrorActionPreference = "Stop"
$launcher = Join-Path $PSScriptRoot "iniciar_myra_desktop.ps1"
if (-not (Test-Path $launcher)) { throw "Launcher nativo MYRA n?o encontrado: $launcher" }
& $launcher
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
