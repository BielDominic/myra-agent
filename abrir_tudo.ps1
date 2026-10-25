Write-Host "Iniciando MYRA (Ollama + Backend + Widget)..." -ForegroundColor Cyan

# 0. Atualiza as variaveis do usuario antes de iniciar os servicos.
try {
    & (Join-Path $PSScriptRoot "scripts\import_user_environment.ps1")
} catch {
    Write-Host ("ERRO ao carregar configuracao: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}

# 1. Garante que o modelo local esta disponivel antes de subir o planner.
try {
    & (Join-Path $PSScriptRoot "scripts\ensure_ollama.ps1")
} catch {
    Write-Host ("ERRO: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}

# 1. Encerra apenas o backend MYRA e valida a porta; nunca mata Python alheio.
try {
    & (Join-Path $PSScriptRoot "scripts\stop_myra_backend.ps1")
} catch {
    Write-Host ("ERRO: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
Get-Process -Name "myra-widget" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1

# 2. Inicia o Backend (Python)
Write-Host "Subindo Backend (FastAPI)..." -ForegroundColor Yellow
Start-Process "C:\computer-agent\venv\Scripts\python.exe" -ArgumentList "agent.py" -WorkingDirectory "C:\computer-agent" -WindowStyle Hidden

# 3. Inicia o Widget (Tauri)
Write-Host "Subindo Widget (Tauri)..." -ForegroundColor Yellow
$widgetPath = "C:\computer-agent\src-tauri\target\debug\myra-widget.exe"
if (Test-Path $widgetPath) {
    Start-Process $widgetPath
} else {
    Write-Host "AVISO: Executavel do widget nao encontrado. Compile com 'cargo build' na pasta src-tauri." -ForegroundColor Red
}

Write-Host "MYRA iniciado com sucesso!" -ForegroundColor Green