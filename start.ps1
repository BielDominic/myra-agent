# start.ps1 - Sobe todos os servicos do Computer Agent

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  COMPUTER AGENT - Iniciando ambiente" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# 1. Ollama
Write-Host "[1/4] Verificando Ollama..." -ForegroundColor Yellow
try {
    $null = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 3
    Write-Host "      Ollama ja esta rodando" -ForegroundColor Green
} catch {
    Write-Host "      Ollama nao esta rodando. Iniciando com CUDA v12..." -ForegroundColor Yellow
    taskkill /F /IM "ollama app.exe" 2>$null | Out-Null
    taskkill /F /IM "ollama.exe" 2>$null | Out-Null
    Start-Sleep -Seconds 2
    $env:OLLAMA_LLM_LIBRARY="cuda_v12"
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    $tentativas = 0
    $ok = $false
    while ($tentativas -lt 15 -and -not $ok) {
        Start-Sleep -Seconds 1
        try {
            $null = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 2
            $ok = $true
        } catch { $tentativas++ }
    }
    if ($ok) { Write-Host "      Ollama iniciado" -ForegroundColor Green }
    else { Write-Host "      ERRO: Ollama nao subiu" -ForegroundColor Red }
}

# 2. Docker
Write-Host ""
Write-Host "[2/4] Verificando Docker..." -ForegroundColor Yellow
try {
    $null = docker ps 2>$null
    Write-Host "      Docker esta rodando" -ForegroundColor Green
    $container = docker ps --filter "name=open-webui" --format "{{.Names}}" 2>$null
    if ($container -eq "open-webui") {
        Write-Host "      Container open-webui ativo" -ForegroundColor Green
    } else {
        Write-Host "      Iniciando container open-webui..." -ForegroundColor Yellow
        docker start open-webui 2>$null | Out-Null
        Start-Sleep -Seconds 3
        Write-Host "      Container iniciado" -ForegroundColor Green
    }
} catch {
    Write-Host "      Docker NAO esta rodando. Abra o Docker Desktop." -ForegroundColor Red
}

# 3. Uvicorn
Write-Host ""
Write-Host "[3/4] Verificando agent.py..." -ForegroundColor Yellow
try {
    $null = Invoke-RestMethod -Uri "http://127.0.0.1:8000/" -Method Get -TimeoutSec 3
    Write-Host "      agent.py ja esta rodando" -ForegroundColor Green
} catch {
    Write-Host "      Iniciando agent.py em nova janela..." -ForegroundColor Yellow
    $cmd = "cd C:\computer-agent; Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass; .\venv\Scripts\Activate.ps1; uvicorn agent:app --host 127.0.0.1 --port 8000"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmd
    $tentativas = 0
    $ok = $false
    while ($tentativas -lt 15 -and -not $ok) {
        Start-Sleep -Seconds 1
        try {
            $null = Invoke-RestMethod -Uri "http://127.0.0.1:8000/" -Method Get -TimeoutSec 2
            $ok = $true
        } catch { $tentativas++ }
    }
    if ($ok) { Write-Host "      agent.py iniciado" -ForegroundColor Green }
    else { Write-Host "      ERRO: agent.py nao subiu" -ForegroundColor Red }
}

# 4. Resumo
Write-Host ""
Write-Host "[4/4] Verificacao final..." -ForegroundColor Yellow
Write-Host ""

$ollama_ok = $false
$docker_ok = $false
$agent_ok = $false

try { $null = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 3; $ollama_ok = $true } catch {}
try {
    $c = docker ps --filter "name=open-webui" --format "{{.Names}}" 2>$null
    if ($c -eq "open-webui") { $docker_ok = $true }
} catch {}
try { $null = Invoke-RestMethod -Uri "http://127.0.0.1:8000/" -Method Get -TimeoutSec 3; $agent_ok = $true } catch {}

Write-Host "  Ollama (11434)   : $(if ($ollama_ok) {'[OK]'} else {'[X]'})" -ForegroundColor $(if ($ollama_ok) {'Green'} else {'Red'})
Write-Host "  Open WebUI (3000): $(if ($docker_ok) {'[OK]'} else {'[X]'})" -ForegroundColor $(if ($docker_ok) {'Green'} else {'Red'})
Write-Host "  agent.py (8000)  : $(if ($agent_ok) {'[OK]'} else {'[X]'})" -ForegroundColor $(if ($agent_ok) {'Green'} else {'Red'})

Write-Host ""
if ($ollama_ok -and $docker_ok -and $agent_ok) {
    Write-Host "===============================================" -ForegroundColor Green
    Write-Host "  TUDO PRONTO!  Acesse: http://localhost:3000" -ForegroundColor Green
    Write-Host "===============================================" -ForegroundColor Green
} else {
    Write-Host "===============================================" -ForegroundColor Yellow
    Write-Host "  ATENCAO: Alguns servicos nao subiram" -ForegroundColor Yellow
    Write-Host "===============================================" -ForegroundColor Yellow
}
Write-Host ""
