Write-Host "Iniciando MYRA (Backend + Widget)..." -ForegroundColor Cyan

# 1. Mata processos antigos para evitar duplicidade
Get-Process python, myra-widget -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

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