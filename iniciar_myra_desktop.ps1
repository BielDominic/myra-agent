$ErrorActionPreference = "Stop"
$root = "C:\computer-agent"
$python = Join-Path $root "venv\Scripts\python.exe"
$widget = Join-Path $root "src-tauri\target-fix\debug\myra-widget.exe"
$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "desktop-launcher.log"
function Log($message) { Add-Content -LiteralPath $log -Value ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $message) }
try {
    Set-Location $root
    if (-not (Test-Path $python)) { throw "Python do ambiente MYRA não encontrado: $python" }
    if (-not (Test-Path $widget)) { throw "Executável da interface MYRA não encontrado: $widget" }

    # Importa as variáveis configuradas pelo usuário sem imprimir segredos.
    & (Join-Path $root "scripts\import_user_environment.ps1") *> (Join-Path $logDir "desktop-environment.log")

    # Ollama permanece independente e é iniciado somente se a API local estiver indisponível.
    & (Join-Path $root "scripts\ensure_ollama.ps1") *> (Join-Path $logDir "desktop-ollama.log")
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "Falha ao preparar Ollama." }

    # Inicia o backend apenas quando a API não responde; não encerra processos existentes.
    $backendReady = $false
    try {
        $null = Invoke-RestMethod -Uri "http://127.0.0.1:8000/" -TimeoutSec 2
        $backendReady = $true
    } catch {}
    if (-not $backendReady) {
        $args = @("-m", "uvicorn", "agent:app", "--host", "127.0.0.1", "--port", "8000")
        Start-Process -FilePath $python -ArgumentList $args -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir "backend-stdout.log") -RedirectStandardError (Join-Path $logDir "backend-stderr.log") | Out-Null
        for ($i = 0; $i -lt 30; $i++) {
            Start-Sleep -Seconds 1
            try {
                $null = Invoke-RestMethod -Uri "http://127.0.0.1:8000/" -TimeoutSec 2
                $backendReady = $true
                break
            } catch {}
        }
    }
    if (-not $backendReady) { throw "Backend MYRA não respondeu na porta 8000. Consulte logs\backend-stderr.log." }

    # Abre ou restaura a janela principal MYRA Desktop, mesmo com o widget em execução.
    Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class MyraWindowApi {
  public delegate bool EnumProc(IntPtr hWnd, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr lp);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
  [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr hWnd, int cmd);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
}
"@
    $script:desktopHwnd = [IntPtr]::Zero
    $callback = [MyraWindowApi+EnumProc]{
        param($hWnd, $lParam)
        $title = New-Object System.Text.StringBuilder 512
        [void][MyraWindowApi]::GetWindowText($hWnd, $title, 512)
        if ($title.ToString() -eq "MYRA Desktop") {
            $script:desktopHwnd = $hWnd
            return $false
        }
        return $true
    }
    [void][MyraWindowApi]::EnumWindows($callback, [IntPtr]::Zero)

    if ($script:desktopHwnd -ne [IntPtr]::Zero) {
        [void][MyraWindowApi]::ShowWindowAsync($script:desktopHwnd, 9)
        [void][MyraWindowApi]::SetForegroundWindow($script:desktopHwnd)
        Log "Janela MYRA Desktop restaurada e trazida para frente."
    } else {
        # Reinicia apenas o executável MYRA exato para carregar a janela desktop do novo build.
        $oldProcesses = @(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -eq "myra-widget.exe" -and $_.ExecutablePath -eq $widget
        })
        foreach ($old in $oldProcesses) {
            Stop-Process -Id ([int]$old.ProcessId) -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 1
        Start-Process -FilePath $widget -WorkingDirectory $root | Out-Null
        for ($i = 0; $i -lt 15; $i++) {
            Start-Sleep -Seconds 1
            $script:desktopHwnd = [IntPtr]::Zero
            [void][MyraWindowApi]::EnumWindows($callback, [IntPtr]::Zero)
            if ($script:desktopHwnd -ne [IntPtr]::Zero) { break }
        }
        if ($script:desktopHwnd -eq [IntPtr]::Zero) {
            throw "MYRA iniciou, mas a janela MYRA Desktop não apareceu. Consulte logs do aplicativo."
        }
        [void][MyraWindowApi]::ShowWindowAsync($script:desktopHwnd, 5)
        [void][MyraWindowApi]::SetForegroundWindow($script:desktopHwnd)
        Log "MYRA Desktop iniciado e janela principal exibida."
    }
    Log "MYRA pronta: Ollama verificado, backend disponível e interface principal aberta."
} catch {
    Log ("ERRO: " + $_.Exception.Message)
    exit 1
}
