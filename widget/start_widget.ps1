# ============================================================
# start_widget.ps1 — Abre o widget da MYRA
# ============================================================

Write-Host "=== MYRA Widget ===" -ForegroundColor Cyan
Write-Host ""

# 1. Verifica se o agent.py está no ar
Write-Host "[1/3] Verificando agent.py..." -ForegroundColor Yellow
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/" -Method Get -TimeoutSec 3
    if ($resp.status -eq "online") {
        Write-Host "      agent.py online" -ForegroundColor Green
    } else {
        Write-Host "      agent.py respondeu, mas status inesperado: $($resp.status)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "      agent.py NAO esta rodando!" -ForegroundColor Red
    Write-Host "      Inicie primeiro: .\iniciar_myra.ps1" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Pressione qualquer tecla para continuar mesmo assim..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# 2. Verifica se os arquivos do widget existem
Write-Host "[2/3] Verificando arquivos do widget..." -ForegroundColor Yellow
$widgetDir = "C:\computer-agent\widget"
$arquivos = @("main.py", "index.html", "style.css", "script.js")
$faltando = @()

foreach ($arq in $arquivos) {
    $path = Join-Path $widgetDir $arq
    if (-not (Test-Path $path)) {
        $faltando += $arq
    }
}

if ($faltando.Count -gt 0) {
    Write-Host "      Faltando: $($faltando -join ', ')" -ForegroundColor Red
    Write-Host "      Verifique se todos os arquivos do widget existem" -ForegroundColor Yellow
    exit 1
}
Write-Host "      Todos os arquivos OK" -ForegroundColor Green

# 3. Abre o widget
Write-Host "[3/3] Abrindo widget..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Pressione Ctrl+C para fechar o widget." -ForegroundColor Cyan
Write-Host ""

Set-Location C:\computer-agent
.\venv\Scripts\python.exe widget\main.py

Write-Host ""
Write-Host "Widget fechado." -ForegroundColor Cyan