# Ensures the local Ollama API is ready before MYRA starts.
# Safe to call repeatedly: it does not restart a healthy server.
$ErrorActionPreference = "Stop"
$endpoint = "http://127.0.0.1:11434/api/tags"

try {
    $null = Invoke-RestMethod -Uri $endpoint -Method Get -TimeoutSec 3
    Write-Host "Ollama ja esta pronto." -ForegroundColor Green
    return
} catch {
    # Start it below only when the API is unavailable.
}

$existing = Get-Process -Name ollama -ErrorAction SilentlyContinue
if ($existing) {
    for ($i = 0; $i -lt 10; $i++) {
        Start-Sleep -Seconds 1
        try {
            $null = Invoke-RestMethod -Uri $endpoint -Method Get -TimeoutSec 2
            Write-Host "Ollama ficou pronto." -ForegroundColor Green
            return
        } catch {}
    }
    throw "O processo Ollama existe, mas a API nao respondeu em $endpoint. Diagnostique o processo antes de iniciar outra instancia."
}

$command = Get-Command ollama.exe -ErrorAction SilentlyContinue
$ollamaPath = if ($command) { $command.Source } else { Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe" }
if (-not (Test-Path -LiteralPath $ollamaPath)) {
    throw "Ollama nao foi encontrado. Instale-o ou ajuste PATH; caminho verificado: $ollamaPath"
}

$library = [Environment]::GetEnvironmentVariable("OLLAMA_LLM_LIBRARY", "Process")
if ([string]::IsNullOrWhiteSpace($library)) {
    $library = [Environment]::GetEnvironmentVariable("OLLAMA_LLM_LIBRARY", "User")
}
if ([string]::IsNullOrWhiteSpace($library)) {
    $library = "cuda_v12"
}
$env:OLLAMA_LLM_LIBRARY = $library

Write-Host "Ollama nao esta respondendo; iniciando o servidor local..." -ForegroundColor Yellow
Start-Process -FilePath $ollamaPath -ArgumentList "serve" -WindowStyle Hidden | Out-Null

for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    try {
        $null = Invoke-RestMethod -Uri $endpoint -Method Get -TimeoutSec 2
        Write-Host "Ollama iniciado e API validada." -ForegroundColor Green
        return
    } catch {}
}
throw "Ollama nao ficou pronto apos 20 segundos. Verifique logs, CUDA e a porta 11434."
