$ErrorActionPreference = "Stop"
$logDir = Join-Path $env:LOCALAPPDATA "MYRA\logs"
$pidFile = Join-Path $logDir "comfyui.pid"
if (-not (Test-Path $pidFile)) { Write-Output "PID do ComfyUI nao encontrado."; exit 0 }
$targetPid = 0
if (-not [int]::TryParse((Get-Content -LiteralPath $pidFile -Raw).Trim(), [ref]$targetPid)) {
    Remove-Item -LiteralPath $pidFile -Force
    throw "Arquivo PID invalido."
}
$proc = Get-CimInstance Win32_Process -Filter "ProcessId = $targetPid"
if ($proc -and $proc.CommandLine -match "ComfyUI\\main.py") {
    Stop-Process -Id $targetPid -Force
    Write-Output "ComfyUI encerrado."
} else {
    Write-Output "Processo PID nao corresponde ao ComfyUI; nenhuma acao executada."
}
Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
