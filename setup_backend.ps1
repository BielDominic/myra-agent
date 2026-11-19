$ErrorActionPreference = "Stop"
$source = Join-Path $PSScriptRoot "backend"
$wheelhouse = Join-Path $PSScriptRoot "wheelhouse"
$playwrightPayload = Join-Path $PSScriptRoot "playwright-browsers"
$runtimeInstaller = Join-Path $PSScriptRoot "runtime\python-3.14.10-amd64.exe"
if (-not (Test-Path (Join-Path $source "agent.py"))) { throw "Arquivos do backend MYRA nao encontrados." }
if (-not (Test-Path $wheelhouse)) { throw "Pacotes offline do MYRA nao encontrados: $wheelhouse" }
if (-not (Test-Path $playwrightPayload)) { throw "Navegador Chromium do Playwright nao encontrado no instalador." }

$installRoot = Join-Path $env:LOCALAPPDATA "MYRA"
$backend = Join-Path $installRoot "backend"
$logs = Join-Path $installRoot "logs"
$workspace = Join-Path $installRoot "workspace"
$profile = Join-Path $installRoot "chrome_profile"
$screenshots = Join-Path $installRoot "screenshots"
New-Item -ItemType Directory -Force -Path $backend,$logs,$workspace,$profile,$screenshots | Out-Null
Write-Host "Instalando arquivos locais da MYRA em $backend"
foreach ($name in @("agent.py","tasks","computer","browser-extension","tools","requirements.txt","requirements-core.txt","requirements-core.lock","requirements-vision.txt","README.md")) {
    $from = Join-Path $source $name
    if (Test-Path $from) { Copy-Item -LiteralPath $from -Destination $backend -Recurse -Force }
}

# Reuse a compatible Python 3.14 installation; otherwise install the signed official runtime bundled with MYRA.
$pythonExe = $null
$pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
if ($pyLauncher) {
    $detected = & $pyLauncher.Source -3.14 -c "import sys; print(sys.executable)" 2>$null
    if ($LASTEXITCODE -eq 0 -and $detected) { $pythonExe = ($detected | Select-Object -Last 1).Trim() }
}
if (-not $pythonExe) {
    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $detectedVersion = & $pythonCommand.Source --version 2>&1 | Out-String
        if ($detectedVersion -match "Python 3\.14\.") { $pythonExe = $pythonCommand.Source }
    }
}
# Find an existing per-user/per-machine Python registration even when PATH and the py launcher are absent.
if (-not $pythonExe) {
    $registryPaths = @(
        "HKCU:\Software\Python\PythonCore\3.14\InstallPath",
        "HKLM:\Software\Python\PythonCore\3.14\InstallPath",
        "HKLM:\Software\WOW6432Node\Python\PythonCore\3.14\InstallPath"
    )
    foreach ($registryPath in $registryPaths) {
        if (Test-Path $registryPath) {
            $key = Get-Item -LiteralPath $registryPath
            $candidate = $key.GetValue("ExecutablePath")
            if (-not $candidate) {
                $installDirectory = $key.GetValue("")
                if ($installDirectory) { $candidate = Join-Path $installDirectory "python.exe" }
            }
            if ($candidate -and (Test-Path $candidate)) { $pythonExe = $candidate; break }
        }
    }
}
if (-not $pythonExe) {
    if (-not (Test-Path $runtimeInstaller)) { throw "Runtime Python 3.14 nao encontrado no instalador." }
    $pythonRoot = Join-Path $env:LOCALAPPDATA "Programs\Python\Python314"
    Write-Host "Instalando Python 3.14.10 incluido no instalador..."
    $arguments = @("/quiet","InstallAllUsers=0","Include_pip=1","Include_launcher=0","PrependPath=0","Include_test=0","Shortcuts=0")
    $process = Start-Process -FilePath $runtimeInstaller -ArgumentList $arguments -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "Instalacao do Python falhou (codigo $($process.ExitCode))." }
    $pythonExe = Join-Path $pythonRoot "python.exe"
}
if (-not (Test-Path $pythonExe)) { throw "Python 3.14 nao foi instalado corretamente." }
$version = & $pythonExe --version 2>&1 | Out-String
if ($version -notmatch "Python 3\.14\.") { throw "MYRA requer Python 3.14. Detectado: $version" }
Write-Host "Runtime selecionado: $pythonExe ($version.Trim())"

$venvPython = Join-Path $backend "venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    & $pythonExe -m venv (Join-Path $backend "venv")
    if ($LASTEXITCODE -ne 0) { throw "Nao foi possivel criar o ambiente Python virtual." }
}
Write-Host "Instalando dependencias principais a partir do pacote offline incluido..."
& $venvPython -m pip install --no-index --find-links $wheelhouse -r (Join-Path $backend "requirements-core.txt")
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependencias offline do MYRA." }

$installedBrowsers = Join-Path $installRoot "playwright-browsers"
if (Test-Path $installedBrowsers) { Remove-Item $installedBrowsers -Recurse -Force }
New-Item -ItemType Directory -Force -Path $installedBrowsers | Out-Null
Copy-Item -Path (Join-Path $playwrightPayload "*") -Destination $installedBrowsers -Recurse -Force

$repo = Join-Path $installRoot "repo"
if (Get-Command gh.exe -ErrorAction SilentlyContinue) { try { & gh auth setup-git *> $null } catch { Write-Warning "GitHub CLI authentication could not be connected to Git." } }
if ($env:MYRA_SKIP_GIT_CLONE -ne "1" -and -not (Test-Path (Join-Path $repo ".git")) -and (Get-Command git.exe -ErrorAction SilentlyContinue)) {
    try { & git clone --depth 1 --branch feature/fase26-vision-fixes https://github.com/BielDominic/myra-agent.git $repo; if ($LASTEXITCODE -ne 0) { Write-Warning "GitHub clone unavailable; GitHub sync remains disabled until a repository is connected." } } catch { Write-Warning "Could not clone repository: $_" }
}
Copy-Item (Join-Path $PSScriptRoot "start_myra.ps1") (Join-Path $installRoot "start_myra.ps1") -Force
$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\MYRA"
New-Item -ItemType Directory -Force -Path $startMenu | Out-Null
$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $startMenu "MYRA.lnk"))
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = ('-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $installRoot "start_myra.ps1") + '"')
$shortcut.WorkingDirectory = $installRoot
$shortcut.Save()
Write-Host "MYRA instalada. Dependencias Python principais instaladas sem baixar pacotes do PyPI."
Write-Host "Abra MYRA pelo menu Iniciar para iniciar backend e interface."
