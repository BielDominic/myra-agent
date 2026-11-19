$ErrorActionPreference = "Stop"
$source = Join-Path $PSScriptRoot "backend"
if (-not (Test-Path (Join-Path $source "agent.py"))) { throw "Arquivos do backend nÃ£o encontrados ao lado do instalador." }
$installRoot = Join-Path $env:LOCALAPPDATA "MYRA"
$backend = Join-Path $installRoot "backend"
$logs = Join-Path $installRoot "logs"
$workspace = Join-Path $installRoot "workspace"
$profile = Join-Path $installRoot "chrome_profile"
$screenshots = Join-Path $installRoot "screenshots"
New-Item -ItemType Directory -Force -Path $backend,$logs,$workspace,$profile,$screenshots | Out-Null
Write-Host "Instalando arquivos locais da MYRA em $backend"
foreach ($name in @("agent.py","tasks","computer","browser-extension","tools","requirements.txt","README.md")) {
    $from = Join-Path $source $name
    if (Test-Path $from) { Copy-Item -LiteralPath $from -Destination $backend -Recurse -Force }
}
$python = Get-Command py.exe -ErrorAction SilentlyContinue
if ($python) {
    $pythonExe = $python.Source
    $previousErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $pythonExe -3.14 --version *> $null
    $pythonExitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorAction
    if ($pythonExitCode -ne 0) { throw "Python 3.14 is required. Install it and retry." }
    $pythonArgs = @("-3.14")
} else {
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $python) { throw "Python 3.14 is required." }
    $version = (& $python.Source --version 2>&1 | Out-String)
    if ($version -notmatch "Python 3\.14\.") { throw "Python 3.14 is required. Detected: $version" }
    $pythonExe = $python.Source
    $pythonArgs = @()
}
$venvPython = Join-Path $backend "venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    & $pythonExe @pythonArgs -m venv (Join-Path $backend "venv")
    if ($LASTEXITCODE -ne 0) { throw "NÃ£o foi possÃ­vel criar o ambiente Python." }
}
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Could not upgrade pip." }
& $venvPython -m pip install -r (Join-Path $backend "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependÃªncias." }
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
Write-Host "Backend MYRA instalado. Atalho criado no menu Iniciar."
Write-Host "Abra MYRA pelo menu Iniciar para iniciar backend e interface."
