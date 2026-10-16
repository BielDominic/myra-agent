# abrir_tudo.ps1 - Abre todos os servicos do MYRA (Computer Agent)

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  MYRA - Abrindo tudo" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# 1. Docker Desktop
Write-Host "[1/6] Abrindo Docker Desktop..." -ForegroundColor Yellow
$dockerPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (Test-Path $dockerPath) {
    Start-Process $dockerPath
    Write-Host "      Docker Desktop iniciado" -ForegroundColor Green
    Write-Host "      Aguardando 30 segundos..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
} else {
    Write-Host "      AVISO: Docker Desktop nao encontrado" -ForegroundColor Red
}

# 2. Ollama (em background, com CUDA v12)
Write-Host ""
Write-Host "[2/6] Verificando Ollama..." -ForegroundColor Yellow
try {
    $null = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 3
    Write-Host "      Ollama ja esta rodando" -ForegroundColor Green
} catch {
    Write-Host "      Iniciando Ollama com CUDA v12..." -ForegroundColor Yellow
    taskkill /F /IM "ollama app.exe" 2>$null | Out-Null
    taskkill /F /IM "ollama.exe" 2>$null | Out-Null
    Start-Sleep -Seconds 2
    $env:OLLAMA_LLM_LIBRARY = "cuda_v12"
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 5
    Write-Host "      Ollama iniciado" -ForegroundColor Green
}

# 3. Container Open WebUI
Write-Host ""
Write-Host "[3/6] Verificando Open WebUI (Docker)..." -ForegroundColor Yellow
try {
    $container = docker ps --filter "name=open-webui-custom" --format "{{.Names}}" 2>$null
    if ($container -eq "open-webui-custom") {
        Write-Host "      Container open-webui-custom ja esta rodando" -ForegroundColor Green
    } else {
        Write-Host "      Iniciando container open-webui-custom..." -ForegroundColor Yellow
        docker start open-webui-custom 2>$null | Out-Null
        Start-Sleep -Seconds 3
        Write-Host "      Container iniciado" -ForegroundColor Green
    }
} catch {
    Write-Host "      AVISO: Docker nao esta respondendo" -ForegroundColor Red
}

# 4. Uvicorn (agent.py)
Write-Host ""
Write-Host "[4/6] Verificando agent.py (Uvicorn)..." -ForegroundColor Yellow
try {
    $null = Invoke-RestMethod -Uri "http://127.0.0.1:8000/" -Method Get -TimeoutSec 3
    Write-Host "      agent.py ja esta rodando" -ForegroundColor Green
} catch {
    Write-Host "      Iniciando agent.py em nova janela..." -ForegroundColor Yellow
    $env:GMAIL_USER = [System.Environment]::GetEnvironmentVariable('GMAIL_USER', 'User')
    $env:GMAIL_APP_PASSWORD = [System.Environment]::GetEnvironmentVariable('GMAIL_APP_PASSWORD', 'User')
    $env:MYRA_BROWSER_BRIDGE_TOKEN = "a936ffb3ea61433407a3e4df8d91529c1a8754e2a1dbb493c35cf5da8428ec7d"
    $cmd = "cd C:\computer-agent; Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass; .\venv\Scripts\Activate.ps1; `$env:GMAIL_USER='$env:GMAIL_USER'; `$env:GMAIL_APP_PASSWORD='$env:GMAIL_APP_PASSWORD'; `$env:MYRA_BROWSER_BRIDGE_TOKEN='$env:MYRA_BROWSER_BRIDGE_TOKEN'; uvicorn agent:app --host 127.0.0.1 --port 8000"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmd
    Start-Sleep -Seconds 8
    Write-Host "      agent.py iniciado em nova janela" -ForegroundColor Green
}

# 5. llm-eyes (servidor de visao)
Write-Host ""
Write-Host "[5/6] Verificando llm-eyes (visao)..." -ForegroundColor Yellow
try {
    $null = Invoke-RestMethod -Uri "http://127.0.0.1:8081/v1/models" -Method Get -TimeoutSec 3
    Write-Host "      llm-eyes ja esta rodando" -ForegroundColor Green
} catch {
    Write-Host "      Iniciando llm-eyes em nova janela..." -ForegroundColor Yellow
    $modelo = "C:\Users\Administrator\.cache\huggingface\hub\models--unsloth--Qwen3.5-0.8B-GGUF\snapshots\6ab461498e2023f6e3c1baea90a8f0fe38ab64d0\Qwen3.5-0.8B-UD-Q4_K_XL.gguf"
    $mmproj = "C:\computer-agent\llm-eyes\models\mmproj-F16.gguf"
    $cmd = "llama-server -m `"$modelo`" --mmproj `"$mmproj`" -ngl 99 --host 0.0.0.0 --port 8081"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmd
    Start-Sleep -Seconds 15
    Write-Host "      llm-eyes iniciado em nova janela" -ForegroundColor Green
}

# 6. Widget Tauri (FASE 27 - overlay TARS)
Write-Host ""
Write-Host "[6/6] Verificando Widget Tauri..." -ForegroundColor Yellow
$widgetProc = Get-Process -Name "myra-widget" -ErrorAction SilentlyContinue
if ($widgetProc) {
    Write-Host "      Widget Tauri ja esta rodando (PID $($widgetProc.Id -join ','))" -ForegroundColor Green
} else {
    Write-Host "      Iniciando Widget Tauri em nova janela..." -ForegroundColor Yellow
    $cmd = "cd C:\computer-agent\widget-tauri; cargo tauri dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmd
    Start-Sleep -Seconds 5
    Write-Host "      Widget Tauri iniciado em nova janela (build pode demorar ~1 min)" -ForegroundColor Green
}

# Resumo final
Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  VERIFICACAO FINAL" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

$ollama_ok = $false
$docker_ok = $false
$agent_ok = $false
$llm_eyes_ok = $false
$widget_ok = $false

try { $null = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 3; $ollama_ok = $true } catch {}
try {
    $c = docker ps --filter "name=open-webui-custom" --format "{{.Names}}" 2>$null
    if ($c -eq "open-webui-custom") { $docker_ok = $true }
} catch {}
try { $null = Invoke-RestMethod -Uri "http://127.0.0.1:8000/" -Method Get -TimeoutSec 3; $agent_ok = $true } catch {}
try { $null = Invoke-RestMethod -Uri "http://127.0.0.1:8081/v1/models" -Method Get -TimeoutSec 3; $llm_eyes_ok = $true } catch {}
if (Get-Process -Name "myra-widget" -ErrorAction SilentlyContinue) { $widget_ok = $true }

Write-Host "  Ollama (11434)      : $(if ($ollama_ok) {'[OK]'} else {'[X]'})" -ForegroundColor $(if ($ollama_ok) {'Green'} else {'Red'})
Write-Host "  Open WebUI (8080)   : $(if ($docker_ok) {'[OK]'} else {'[X]'})" -ForegroundColor $(if ($docker_ok) {'Green'} else {'Red'})
Write-Host "  agent.py (8000)     : $(if ($agent_ok) {'[OK]'} else {'[X]'})" -ForegroundColor $(if ($agent_ok) {'Green'} else {'Red'})
Write-Host "  llm-eyes (8081)     : $(if ($llm_eyes_ok) {'[OK]'} else {'[X]'})" -ForegroundColor $(if ($llm_eyes_ok) {'Green'} else {'Red'})
Write-Host "  Widget Tauri        : $(if ($widget_ok) {'[OK]'} else {'[X]'})" -ForegroundColor $(if ($widget_ok) {'Green'} else {'Red'})
Write-Host ""

if ($ollama_ok -and $docker_ok -and $agent_ok) {
    Write-Host "===============================================" -ForegroundColor Green
    Write-Host "  TUDO PRONTO!" -ForegroundColor Green
    Write-Host "  Acesse: http://localhost:8080 (no Edge)" -ForegroundColor Green
    Write-Host "===============================================" -ForegroundColor Green
} else {
    Write-Host "===============================================" -ForegroundColor Yellow
    Write-Host "  ATENCAO: Alguns servicos nao subiram" -ForegroundColor Yellow
    Write-Host "  Veja os [X] acima" -ForegroundColor Yellow
    Write-Host "===============================================" -ForegroundColor Yellow
}
Write-Host ""