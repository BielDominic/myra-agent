# Stop only MYRA's own backend process; never kill unrelated Python apps.
$ErrorActionPreference = "Stop"
$repoPath = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot)).TrimEnd("\")
$repoPattern = [regex]::Escape($repoPath)

$myraProcesses = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match "^python(w)?\.exe$" -and
    $_.CommandLine -match "(?i)(agent\.py|uvicorn\s+agent:app)" -and
    $_.CommandLine -match $repoPattern
})
$myraPids = @($myraProcesses | ForEach-Object { [int]$_.ProcessId })
$listeners = @(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)
$foreignListeners = @($listeners | Where-Object { $myraPids -notcontains [int]$_.OwningProcess })

if ($foreignListeners.Count -gt 0) {
    $owners = ($foreignListeners | ForEach-Object { "$($_.LocalAddress):$($_.LocalPort) PID $($_.OwningProcess)" }) -join ", "
    throw "Porta 8000 ocupada por processo que nao foi identificado como backend MYRA: $owners. Nenhum processo alheio foi encerrado."
}

if ($myraPids.Count -gt 0) {
    Write-Host ("Encerrando apenas backend(s) MYRA identificado(s): " + ($myraPids -join ", ")) -ForegroundColor Yellow
    foreach ($pidToStop in $myraPids) {
        Stop-Process -Id $pidToStop -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

$remainingListeners = @(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)
if ($remainingListeners.Count -gt 0) {
    $owners = ($remainingListeners | ForEach-Object { "PID $($_.OwningProcess)" }) -join ", "
    throw "A porta 8000 continua ocupada ($owners). Nenhum processo adicional foi encerrado."
}
Write-Host "Backend MYRA parado com seguranca; porta 8000 livre." -ForegroundColor Green
