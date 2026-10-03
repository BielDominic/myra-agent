# MYRA - Script de inicializacao do backend (agent.py)
$ErrorActionPreference = "Continue"

Write-Host "`n[1/4] Parando agent.py antigo..." -ForegroundColor Cyan
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

Write-Host "[2/4] Liberando porta 8000..." -ForegroundColor Cyan
$port = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($port) {
    Write-Host "  Porta ocupada. Matando..." -ForegroundColor Yellow
    Stop-Process -Id $port.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}
Write-Host "  OK" -ForegroundColor Green

Write-Host "[3/4] Ativando venv..." -ForegroundColor Cyan
Set-Location C:\computer-agent
& .\venv\Scripts\Activate.ps1

Write-Host "[4/4] Subindo MYRA backend..." -ForegroundColor Cyan
Write-Host "`n============================================" -ForegroundColor Green
Write-Host "  MYRA BACKEND - Servidor rodando" -ForegroundColor Green
Write-Host "  Endpoint: http://localhost:8000" -ForegroundColor Green
Write-Host "  Ctrl+C para parar" -ForegroundColor Green
Write-Host "============================================`n" -ForegroundColor Green

python agent.py