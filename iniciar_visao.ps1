$ErrorActionPreference = "Continue"

Write-Host "`n[1/3] Verificando arquivos..." -ForegroundColor Cyan

$llama = "C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Packages\ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe\llama-server.exe"
$modelo = "C:\computer-agent\llm-eyes\models\Qwen3.5-0.8B-UD-Q4_K_XL.gguf"
$mmproj = "C:\computer-agent\llm-eyes\models\mmproj-F16.gguf"

if (-not (Test-Path $llama)) { Write-Host "  ERRO: llama-server.exe nao encontrado" -ForegroundColor Red; exit 1 }
if (-not (Test-Path $modelo)) { Write-Host "  ERRO: modelo nao encontrado" -ForegroundColor Red; exit 1 }
if (-not (Test-Path $mmproj)) { Write-Host "  ERRO: mmproj nao encontrado" -ForegroundColor Red; exit 1 }

Write-Host "  OK - todos os arquivos presentes" -ForegroundColor Green

Write-Host "`n[2/3] Liberando porta 8081..." -ForegroundColor Cyan
$port = Get-NetTCPConnection -LocalPort 8081 -State Listen -ErrorAction SilentlyContinue
if ($port) {
    Write-Host "  Porta ocupada. Matando..." -ForegroundColor Yellow
    Stop-Process -Id $port.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

Write-Host "`n[3/3] Subindo llama-server (visao)..." -ForegroundColor Cyan
Write-Host "`n============================================" -ForegroundColor Green
Write-Host "  MYRA VISAO - Servidor rodando" -ForegroundColor Green
Write-Host "  Endpoint: http://localhost:8081" -ForegroundColor Green
Write-Host "  Ctrl+C para parar" -ForegroundColor Green
Write-Host "============================================`n" -ForegroundColor Green

& $llama -m $modelo --mmproj $mmproj -ngl 99 --host 0.0.0.0 --port 8081