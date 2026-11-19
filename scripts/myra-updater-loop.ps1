# MYRA background update watcher. Started at user logon by a Startup-folder shortcut.
$ErrorActionPreference = 'SilentlyContinue'
$updater = Join-Path $PSScriptRoot 'myra-updater.ps1'
while (Test-Path -LiteralPath $updater) {
    $installed = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -eq 'MYRA' } | Select-Object -First 1
    if (-not $installed) { break }
    $widgetRunning = Get-Process -Name 'myra-widget' -ErrorAction SilentlyContinue
    $backendRunning = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('python.exe', 'pythonw.exe') -and
        $_.CommandLine -match '(?i)(-m\s+uvicorn\s+agent:app|agent\.py)'
    }
    if (-not $widgetRunning -and -not $backendRunning) {
        & $updater
    }
    Start-Sleep -Seconds 21600
}
