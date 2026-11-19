param([switch]$InstallStartup)

$ErrorActionPreference = "Stop"
if ($InstallStartup) {
    $startup = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
    New-Item -ItemType Directory -Force -Path $startup | Out-Null
    $shortcutPath = Join-Path $startup "MYRA Image Engine.lnk"
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = Join-Path $PSHOME "powershell.exe"
    $shortcut.Arguments = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$PSCommandPath`""
    $shortcut.WindowStyle = 7
    $shortcut.Save()
    Write-Output "ComfyUI configurado para iniciar no logon do Windows."
    exit 0
}
$root = Join-Path $env:LOCALAPPDATA "MYRA\ComfyUI"
$portable = if (Test-Path (Join-Path $root "python_embeded\python.exe")) { $root } else { Join-Path $root "ComfyUI_windows_portable" }
$python = Join-Path $portable "python_embeded\python.exe"
$main = Join-Path $portable "ComfyUI\main.py"
$checkpointDir = Join-Path $portable "ComfyUI\models\checkpoints"
$logDir = Join-Path $env:LOCALAPPDATA "MYRA\logs"
$pidFile = Join-Path $logDir "comfyui.pid"
$stdout = Join-Path $logDir "comfyui.stdout.log"
$stderr = Join-Path $logDir "comfyui.stderr.log"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

if (-not (Test-Path $python) -or -not (Test-Path $main)) {
    throw "ComfyUI portable nao encontrado em $root. Extraia o pacote oficial e instale um checkpoint."
}
if (-not (Get-ChildItem -LiteralPath $checkpointDir -Filter "*.safetensors" -File -ErrorAction SilentlyContinue)) {
    throw "Nenhum checkpoint .safetensors encontrado em $checkpointDir."
}

try {
    $health = Invoke-RestMethod "http://127.0.0.1:8188/system_stats" -TimeoutSec 2
    if ($health) { Write-Output "ComfyUI ja esta online em 127.0.0.1:8188."; exit 0 }
} catch {}

$existing = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -in @("python.exe", "pythonw.exe") -and
    $_.CommandLine -match [regex]::Escape($main) -and
    $_.CommandLine -match "--port\s+8188"
} | Select-Object -First 1
if ($existing) {
    Set-Content -LiteralPath $pidFile -Value $existing.ProcessId
    Write-Output "ComfyUI ja esta em inicializacao (PID $($existing.ProcessId))."
    exit 0
}

$comfyArgs = @(
    "-s", "`"$main`"",
    "--windows-standalone-build",
    "--lowvram",
    "--cpu-vae",
    "--listen", "127.0.0.1",
    "--port", "8188"
)
$process = Start-Process -FilePath $python -ArgumentList $comfyArgs -WorkingDirectory $portable -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
Set-Content -LiteralPath $pidFile -Value $process.Id

$deadline = (Get-Date).AddSeconds(90)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 3
    try {
        $health = Invoke-RestMethod "http://127.0.0.1:8188/system_stats" -TimeoutSec 3
        if ($health) { Write-Output "ComfyUI online (PID $($process.Id))."; exit 0 }
    } catch {}
    if ($process.HasExited) {
        throw "ComfyUI encerrou com codigo $($process.ExitCode). Consulte $stderr."
    }
}
throw "ComfyUI nao respondeu em 90 segundos. Consulte $stdout e $stderr."
