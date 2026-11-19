$ErrorActionPreference = "Stop"
$root = Join-Path $env:LOCALAPPDATA "MYRA"
$backend = Join-Path $root "backend"
$python = Join-Path $backend "venv\Scripts\python.exe"
$logs = Join-Path $root "logs"
$env:MYRA_DATA_DIR = $root
$env:MYRA_WORKSPACE = Join-Path $root "workspace"
$env:MYRA_CHROME_PROFILE = Join-Path $root "chrome_profile"
$env:MYRA_SCREENSHOTS = Join-Path $root "screenshots"
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $root "playwright-browsers"
$env:MYRA_NOTES_FILE = Join-Path $root "notes.txt"
$repo = Join-Path $root "repo"
$env:MYRA_REPO_ROOT = if (Test-Path (Join-Path $repo ".git")) { $repo } else { $backend }
$env:MYRA_REA_ALLOWED_ROOTS = $env:MYRA_WORKSPACE
New-Item -ItemType Directory -Force -Path $logs | Out-Null
if (-not (Test-Path $python)) { throw "Backend não instalado. Execute setup_backend.ps1 primeiro." }
$ready = $false
try { $null = Invoke-RestMethod "http://127.0.0.1:8000/" -TimeoutSec 2; $ready = $true } catch {}
if (-not $ready) {
    Start-Process -FilePath $python -ArgumentList @("-m","uvicorn","agent:app","--host","127.0.0.1","--port","8000") -WorkingDirectory $backend -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs "backend-stdout.log") -RedirectStandardError (Join-Path $logs "backend-stderr.log") | Out-Null
    for ($i=0; $i -lt 45; $i++) {
        Start-Sleep -Seconds 1
        try { $null = Invoke-RestMethod "http://127.0.0.1:8000/" -TimeoutSec 2; $ready = $true; break } catch {}
    }
}
if (-not $ready) { throw "Backend MYRA não iniciou. Consulte $logs\backend-stderr.log" }
$candidates = @(
    (Join-Path $env:LOCALAPPDATA "MYRA\myra-widget.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\MYRA\myra-widget.exe"),
    (Join-Path $env:ProgramFiles "MYRA\myra-widget.exe")
)
$app = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $app) { throw "Executável MYRA não encontrado nos caminhos padrão. Reinstale o aplicativo." }
Start-Process -FilePath $app -WorkingDirectory (Split-Path $app)
