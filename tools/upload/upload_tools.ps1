# ============================================================
# MYRA - Script de upload automatico das Tools no Open WebUI
# ============================================================
# Uso: .\upload_tools.ps1
# Precisa da variavel OPENWEBUI_API_KEY definida
# ============================================================

$ErrorActionPreference = "Continue"

$OpenWebUIUrl = "http://127.0.0.1:8080"
$ApiKey = $env:OPENWEBUI_API_KEY

if (-not $ApiKey) {
    Write-Host "ERRO: variavel OPENWEBUI_API_KEY nao definida." -ForegroundColor Red
    Write-Host "Rode: [System.Environment]::SetEnvironmentVariable('OPENWEBUI_API_KEY', 'sk-sua-key', 'User')" -ForegroundColor Yellow
    exit 1
}

$Headers = @{
    "Authorization" = "Bearer $ApiKey"
    "Content-Type"  = "application/json"
}

$toolsDir = "C:\computer-agent\tools"

$tools = @(
    @{ Name = "BrowserAgent";   File = "browseragent.py";   Description = "Navegador, email, arquivos, automacao do PC" },
    @{ Name = "CodeAgent";      File = "codeagent.py";      Description = "Programacao (gerar, explicar, refatorar, testar)" },
    @{ Name = "Visuals Core";   File = "visuals_core.py";   Description = "Graficos, tabelas, heatmaps, timelines" }
)

Write-Host "`n=== Upload de Tools para o Open WebUI ===" -ForegroundColor Cyan
Write-Host "URL: $OpenWebUIUrl" -ForegroundColor Gray
Write-Host ""

foreach ($tool in $tools) {
    $caminho = Join-Path $toolsDir $tool.File
    if (-not (Test-Path $caminho)) {
        Write-Host "[SKIP] $($tool.Name) - arquivo nao encontrado: $caminho" -ForegroundColor Yellow
        continue
    }

    $conteudo = Get-Content $caminho -Raw -Encoding UTF8

    $payload = @{
        id = $tool.Name
        name = $tool.Name
        content = $conteudo
        meta = @{
            description = $tool.Description
        }
    } | ConvertTo-Json -Depth 10

    try {
        $resp = Invoke-RestMethod -Uri "$OpenWebUIUrl/api/v1/tools/create" -Method Post -Headers $Headers -Body $payload
        Write-Host "[OK] $($tool.Name) - importado com sucesso" -ForegroundColor Green
    } catch {
        Write-Host "[ERRO] $($tool.Name) - $($_.Exception.Message)" -ForegroundColor Red
        if ($_.ErrorDetails.Message) {
            Write-Host "  Detalhe: $($_.ErrorDetails.Message)" -ForegroundColor DarkRed
        }
    }
}

Write-Host ""
Write-Host "=== Concluido ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "IMPORTANTE: as tools foram importadas mas PRECISAM ser vinculadas ao modelo:" -ForegroundColor Yellow
Write-Host "  1. Admin Settings -> Models -> Local Agent -> Tools" -ForegroundColor Yellow
Write-Host "  2. Marcar: BrowserAgent + CodeAgent + Visuals Core" -ForegroundColor Yellow
Write-Host "  3. Save" -ForegroundColor Yellow
Write-Host ""