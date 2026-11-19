$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.Text = "MYRA - Configurar inteligência local"
$form.Size = New-Object System.Drawing.Size(520,330)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.BackColor = [System.Drawing.Color]::FromArgb(18,18,27)
$form.ForeColor = [System.Drawing.Color]::White

$title = New-Object System.Windows.Forms.Label
$title.Text = "Configure seu modelo de IA"
$title.Font = New-Object System.Drawing.Font("Segoe UI",16,[System.Drawing.FontStyle]::Bold)
$title.Location = New-Object System.Drawing.Point(24,20)
$title.Size = New-Object System.Drawing.Size(450,32)
$form.Controls.Add($title)

$description = New-Object System.Windows.Forms.Label
$description.Text = "A MYRA funciona com modelos locais. Você pode instalar o Ollama e baixar um modelo agora ou fazer isso depois nas configurações."
$description.Location = New-Object System.Drawing.Point(26,62)
$description.Size = New-Object System.Drawing.Size(450,52)
$form.Controls.Add($description)

$enable = New-Object System.Windows.Forms.CheckBox
$enable.Text = "Instalar Ollama e baixar um modelo agora (recomendado)"
$enable.Checked = $true
$enable.Location = New-Object System.Drawing.Point(28,130)
$enable.Size = New-Object System.Drawing.Size(450,28)
$form.Controls.Add($enable)

$modelLabel = New-Object System.Windows.Forms.Label
$modelLabel.Text = "Modelo inicial:"
$modelLabel.Location = New-Object System.Drawing.Point(28,174)
$modelLabel.Size = New-Object System.Drawing.Size(110,24)
$form.Controls.Add($modelLabel)

$model = New-Object System.Windows.Forms.ComboBox
$model.DropDownStyle = "DropDownList"
$model.Location = New-Object System.Drawing.Point(140,170)
$model.Size = New-Object System.Drawing.Size(330,28)
[void]$model.Items.Add("qwen2.5:3b - recomendado (leve, ferramentas)")
[void]$model.Items.Add("qwen2.5:7b - melhor qualidade, mais RAM")
[void]$model.Items.Add("llama3.2:3b - alternativa leve")
[void]$model.Items.Add("qwen2.5:1.5b - computadores modestos")
$model.SelectedIndex = 0
$form.Controls.Add($model)

$note = New-Object System.Windows.Forms.Label
$note.Text = "O download do modelo pode levar alguns minutos e requer internet. Você poderá trocar o modelo depois."
$note.ForeColor = [System.Drawing.Color]::LightGray
$note.Location = New-Object System.Drawing.Point(28,212)
$note.Size = New-Object System.Drawing.Size(450,38)
$form.Controls.Add($note)

$continue = New-Object System.Windows.Forms.Button
$continue.Text = "Continuar"
$continue.Location = New-Object System.Drawing.Point(355,255)
$continue.Size = New-Object System.Drawing.Size(115,32)
$continue.DialogResult = [System.Windows.Forms.DialogResult]::OK
$form.Controls.Add($continue)
$skip = New-Object System.Windows.Forms.Button
$skip.Text = "Configurar depois"
$skip.Location = New-Object System.Drawing.Point(225,255)
$skip.Size = New-Object System.Drawing.Size(120,32)
$skip.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
$form.Controls.Add($skip)
$form.AcceptButton = $continue
$form.CancelButton = $skip

if ($form.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK -or -not $enable.Checked) {
    Write-Host "Ollama/model setup skipped by user."
    exit 0
}

$models = @("qwen2.5:3b","qwen2.5:7b","llama3.2:3b","qwen2.5:1.5b")
$selectedModel = $models[$model.SelectedIndex]
$ollama = (Get-Command ollama.exe -ErrorAction SilentlyContinue).Source
if (-not $ollama) {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"),
        (Join-Path $env:ProgramFiles "Ollama\ollama.exe")
    )
    $ollama = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $ollama) {
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Host "Installing Ollama using Windows Package Manager..."
        $install = Start-Process -FilePath $winget.Source -ArgumentList @("install","--id","Ollama.Ollama","-e","--silent","--accept-package-agreements","--accept-source-agreements") -Wait -PassThru -NoNewWindow
        if ($install.ExitCode -ne 0) {
            [System.Windows.Forms.MessageBox]::Show("Não foi possível instalar o Ollama automaticamente. Instale pelo site ollama.com/download e execute MYRA novamente.","MYRA", "OK", "Warning") | Out-Null
            Start-Process "https://ollama.com/download/windows"
            exit 0
        }
    } else {
        [System.Windows.Forms.MessageBox]::Show("O Windows Package Manager não está disponível. Abra o site oficial para instalar o Ollama e depois execute MYRA novamente.","MYRA", "OK", "Information") | Out-Null
        Start-Process "https://ollama.com/download/windows"
        exit 0
    }
    Start-Sleep -Seconds 4
    $ollama = (Get-Command ollama.exe -ErrorAction SilentlyContinue).Source
    if (-not $ollama) {
        $ollama = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    }
}
if (-not (Test-Path $ollama)) { throw "Ollama foi instalado, mas ollama.exe não foi localizado." }

$running = $false
try { $null = Invoke-RestMethod "http://127.0.0.1:11434/api/tags" -TimeoutSec 2; $running = $true } catch {}
if (-not $running) {
    Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden | Out-Null
    for ($i=0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        try { $null = Invoke-RestMethod "http://127.0.0.1:11434/api/tags" -TimeoutSec 2; $running = $true; break } catch {}
    }
}
if (-not $running) { throw "Ollama não iniciou. Abra o Ollama e execute ollama pull $selectedModel." }

Write-Host "Downloading selected local model: $selectedModel"
& $ollama pull $selectedModel
if ($LASTEXITCODE -ne 0) { throw "Falha ao baixar o modelo $selectedModel. Execute ollama pull $selectedModel depois." }

$root = Join-Path $env:LOCALAPPDATA "MYRA"
$config = Join-Path $root "config"
New-Item -ItemType Directory -Force -Path $config | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$modelJson = @{ provider = "ollama"; base_url = "http://127.0.0.1:11434"; model = $selectedModel; installed_at = (Get-Date).ToUniversalTime().ToString("o") } | ConvertTo-Json
[IO.File]::WriteAllText((Join-Path $config "model.json"), $modelJson, $utf8NoBom)
$settingsJson = @{ chat_model = $selectedModel } | ConvertTo-Json
[IO.File]::WriteAllText((Join-Path $root "desktop_settings.json"), $settingsJson, $utf8NoBom)
[System.Windows.Forms.MessageBox]::Show("Ollama e $selectedModel estão prontos. A MYRA poderá usar o modelo local.","MYRA instalada", "OK", "Information") | Out-Null
