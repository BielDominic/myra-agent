$ErrorActionPreference = "Stop"
$root = Join-Path $env:LOCALAPPDATA "MYRA"

# Load per-user secrets and integration settings before starting the backend.
# Never echo these values to the console or logs.
$environmentNames = @(
    "MYRA_BROWSER_BRIDGE_TOKEN",
    "MYRA_REA_ALLOWED_ROOTS",
    "MYRA_REMOTE_API_TOKEN",
    "MYRA_TELEGRAM_ALLOWED_CHAT_IDS",
    "MYRA_TELEGRAM_BOT_TOKEN",
    "MYRA_CORS_ORIGINS",
    "OLLAMA_HOST",
    "OLLAMA_LLM_LIBRARY",
    "OPENWEBUI_API_KEY"
)
foreach ($name in $environmentNames) {
    $value = [Environment]::GetEnvironmentVariable($name, "User")
    [Environment]::SetEnvironmentVariable($name, $value, "Process")
}

$backend = Join-Path $root "backend"
$python = Join-Path $backend "venv\Scripts\python.exe"
$logs = Join-Path $root "logs"
$env:MYRA_DATA_DIR = $root
$env:MYRA_VOICE_ASSET_ROOT = Join-Path $backend "voice-assets"
$env:LEXPHON_DATA_HOME = Join-Path $env:MYRA_VOICE_ASSET_ROOT "lexphon"
$env:HF_HUB_OFFLINE = "1"
$env:HF_HUB_DISABLE_TELEMETRY = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$modelConfig = Join-Path $root "config\model.json"
if (Test-Path $modelConfig) {
    try {
        $selectedModel = (Get-Content $modelConfig -Raw | ConvertFrom-Json).model
        if ($selectedModel) {
            $env:MYRA_CHAT_MODEL = [string]$selectedModel
            $env:MYRA_CODE_MODEL = [string]$selectedModel
            $env:MYRA_PLANNER_MODEL = [string]$selectedModel
        }
    } catch { Write-Warning "Não foi possível ler a configuração do modelo local: $_" }
}
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
$widgetRunning = Get-Process -Name "myra-widget" -ErrorAction SilentlyContinue
if (-not $widgetRunning) {
    Start-Process -FilePath $app -WorkingDirectory (Split-Path $app)
} else {
    Write-Host "MYRA widget ja esta em execucao; mantendo a instancia atual."
}
