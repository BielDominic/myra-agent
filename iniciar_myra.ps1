# MYRA - Script de inicializacao do backend (agent.py)
$ErrorActionPreference = "Continue"

Write-Host "`n[0/5] Carregando ambiente do usuario..." -ForegroundColor Cyan
try {
    & (Join-Path $PSScriptRoot "scripts\import_user_environment.ps1")
} catch {
    Write-Host ("  ERRO: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}

Write-Host "`n[1/5] Verificando Ollama..." -ForegroundColor Cyan
try {
    & (Join-Path $PSScriptRoot "scripts\ensure_ollama.ps1")
} catch {
    Write-Host ("  ERRO: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}

Write-Host "`n[2/5] Parando apenas o backend MYRA anterior..." -ForegroundColor Cyan
try {
    & (Join-Path $PSScriptRoot "scripts\stop_myra_backend.ps1")
} catch {
    Write-Host ("  ERRO: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}

Write-Host "[3/5] Backend anterior encerrado com seguranca." -ForegroundColor Green

Write-Host "[4/5] Ativando venv..." -ForegroundColor Cyan
Set-Location C:\computer-agent
& .\venv\Scripts\Activate.ps1

Write-Host "[5/5] Subindo MYRA backend..." -ForegroundColor Cyan
Write-Host "`n============================================" -ForegroundColor Green
Write-Host "  MYRA BACKEND - Servidor rodando" -ForegroundColor Green
Write-Host "  Endpoint: http://localhost:8000" -ForegroundColor Green
Write-Host "  Ctrl+C para parar" -ForegroundColor Green
Write-Host "============================================`n" -ForegroundColor Green

python agent.py