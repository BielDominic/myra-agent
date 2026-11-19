# MYRA release updater for Windows (current-user installation).
# Checks GitHub Releases, verifies SHA-256, and installs only while MYRA is closed.
$ErrorActionPreference = "Stop"
$repo = "BielDominic/myra-agent"
$logDir = Join-Path $env:LOCALAPPDATA "MYRA\logs"
$log = Join-Path $logDir "auto-update.log"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
function Write-UpdateLog([string]$message) {
    Add-Content -LiteralPath $log -Value ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $message)
}
try {
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/releases/latest" -Headers @{
        "Accept" = "application/vnd.github+json"
        "User-Agent" = "MYRA-AutoUpdater"
    } -TimeoutSec 20
    $latestTag = [string]$release.tag_name
    if ($latestTag -notmatch '^v?(\d+\.\d+\.\d+)$') { throw "Invalid stable release tag." }
    $latestVersion = [version]$Matches[1]

    $installed = Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*" -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -eq "MYRA" -and $_.DisplayVersion } |
        Select-Object -First 1
    if (-not $installed) {
        Write-UpdateLog "No current-user MYRA installation found; skipped."
        return
    }
    $installedVersion = [version]([string]$installed.DisplayVersion).TrimStart("v")
    if ($latestVersion -le $installedVersion) {
        Write-UpdateLog "Already current ($installedVersion)."
        return
    }
    if (Get-Process -Name "myra-widget" -ErrorAction SilentlyContinue) {
        Write-UpdateLog "Update $latestTag deferred because MYRA is running."
        return
    }
    $backendProcesses = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @("python.exe", "pythonw.exe") -and
        $_.CommandLine -match '(?i)(-m\s+uvicorn\s+agent:app|agent\.py)'
    }
    if ($backendProcesses) {
        Write-UpdateLog "Update $latestTag deferred because the MYRA backend is still running."
        return
    }

    $installerName = "MYRA_" + $latestVersion + "_x64-setup.exe"
    $assets = @($release.assets)
    $installerAsset = $assets | Where-Object { $_.name -eq $installerName } | Select-Object -First 1
    $checksumsAsset = $assets | Where-Object { $_.name -eq "SHA256SUMS.txt" } | Select-Object -First 1
    if (-not $installerAsset -or -not $checksumsAsset) { throw "Release is missing installer or checksums." }

    $tempDir = Join-Path $env:TEMP ("MYRA-update-" + $latestVersion)
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
    $installerPath = Join-Path $tempDir $installerName
    $checksumsPath = Join-Path $tempDir "SHA256SUMS.txt"
    Invoke-WebRequest -Uri $checksumsAsset.browser_download_url -OutFile $checksumsPath -TimeoutSec 90
    Invoke-WebRequest -Uri $installerAsset.browser_download_url -OutFile $installerPath -TimeoutSec 600

    $checksumLine = Get-Content -LiteralPath $checksumsPath |
        Where-Object { $_ -match ("^\s*([A-Fa-f0-9]{64})\s+\*?" + [regex]::Escape($installerName) + "\s*$") } |
        Select-Object -First 1
    if (-not $checksumLine -or $checksumLine -notmatch '^\s*([A-Fa-f0-9]{64})') {
        throw "No SHA-256 entry found for $installerName."
    }
    $expectedHash = $Matches[1].ToUpperInvariant()
    $actualHash = (Get-FileHash -LiteralPath $installerPath -Algorithm SHA256).Hash.ToUpperInvariant()
    if ($actualHash -ne $expectedHash) {
        Remove-Item -LiteralPath $installerPath -Force -ErrorAction SilentlyContinue
        throw "SHA-256 verification failed; installer was not executed."
    }

    # Re-check after download and checksum work: MYRA may have opened meanwhile.
    if (Get-Process -Name "myra-widget" -ErrorAction SilentlyContinue) {
        Write-UpdateLog "Update $latestTag deferred because MYRA opened during download."
        return
    }
    $backendProcesses = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @("python.exe", "pythonw.exe") -and
        $_.CommandLine -match '(?i)(-m\s+uvicorn\s+agent:app|agent\.py)'
    }
    if ($backendProcesses) {
        Write-UpdateLog "Update $latestTag deferred because the MYRA backend opened during download."
        return
    }

    Write-UpdateLog "Installing verified release $latestTag (from $installedVersion)."
    $process = Start-Process -FilePath $installerPath -ArgumentList "/S" -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw ("Installer exited with code " + $process.ExitCode + ".") }
    Write-UpdateLog "Installer completed for $latestTag."
} catch {
    Write-UpdateLog ("Update check failed safely: " + $_.Exception.Message)
    return
}
