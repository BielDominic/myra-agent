# MYRA background update watcher. Started at user logon by a Startup-folder shortcut.
# Check every 15 minutes. The updater itself safely defers installation while MYRA
# or its backend is running, then installs the verified release after the user exits.
$ErrorActionPreference = 'SilentlyContinue'
$updater = Join-Path $PSScriptRoot 'myra-updater.ps1'
while (Test-Path -LiteralPath $updater) {
    $installed = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -eq 'MYRA' } | Select-Object -First 1
    if (-not $installed) { break }
    & $updater
    Start-Sleep -Seconds 900
}
