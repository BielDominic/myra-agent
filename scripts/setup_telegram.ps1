# Configura o bot Telegram do MYRA sem gravar segredos no repositorio.
# Execute localmente no PC: powershell -ExecutionPolicy Bypass -File .\scripts\setup_telegram.ps1
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "MYRA - Configuracao segura do Telegram" -ForegroundColor Cyan
Write-Host "Se o token ja foi compartilhado em mensagens, revogue-o no @BotFather e use um token novo."
Write-Host "Antes de continuar, abra o bot no Telegram e envie /start."
Write-Host ""

$secureToken = Read-Host "Cole o NOVO token do bot (entrada oculta)" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
try {
    $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}

if ([string]::IsNullOrWhiteSpace($token) -or $token -notmatch '^\d+:[A-Za-z0-9_-]{20,}$') {
    Write-Error "Formato de token invalido. Nenhuma variavel foi alterada."
    exit 1
}

try {
    # O token fica apenas em memoria e na URL HTTPS desta chamada; nunca imprimir a URL.
    $me = Invoke-RestMethod -Method Get -Uri ("https://api.telegram.org/bot{0}/getMe" -f $token) -TimeoutSec 15
    if (-not $me.ok) { throw "Telegram nao validou o token." }
    Write-Host ("Bot validado: @{0}" -f $me.result.username) -ForegroundColor Green

    $updates = Invoke-RestMethod -Method Get -Uri ("https://api.telegram.org/bot{0}/getUpdates?timeout=0&allowed_updates=%5B%22message%22%5D" -f $token) -TimeoutSec 15
    if (-not $updates.ok) { throw "Nao foi possivel consultar mensagens do bot." }
} catch {
    $token = $null
    Write-Error "Falha ao validar o bot ou consultar mensagens. Confira o token e tente novamente; detalhes sensiveis foram omitidos."
    exit 1
}

$chatIds = @(
    $updates.result |
        Where-Object { $_.message -and $_.message.chat.id -and $_.message.text } |
        ForEach-Object { [string]$_.message.chat.id } |
        Select-Object -Unique
)
if ($chatIds.Count -eq 0) {
    $token = $null
    Write-Host "Nenhuma mensagem encontrada. Envie /start ao bot no Telegram e execute este script novamente." -ForegroundColor Yellow
    exit 2
}

Write-Host ""
Write-Host "Chats encontrados nas mensagens recentes:"
for ($i = 0; $i -lt $chatIds.Count; $i++) {
    Write-Host ("  [{0}] chat ID: {1}" -f ($i + 1), $chatIds[$i])
}
$choice = Read-Host "Escolha o numero do SEU chat autorizado"
$index = 0
if (-not [int]::TryParse($choice, [ref]$index) -or $index -lt 1 -or $index -gt $chatIds.Count) {
    $token = $null
    Write-Error "Selecao invalida. Nenhuma variavel foi alterada."
    exit 1
}
$allowedId = $chatIds[$index - 1]

[Environment]::SetEnvironmentVariable("MYRA_TELEGRAM_BOT_TOKEN", $token, "User")
[Environment]::SetEnvironmentVariable("MYRA_TELEGRAM_ALLOWED_CHAT_IDS", $allowedId, "User")
$token = $null
$secureToken.Dispose()

Write-Host ""
Write-Host "Configuracao salva no ambiente do usuario do Windows." -ForegroundColor Green
Write-Host ("Chat autorizado: {0}" -f $allowedId)
Write-Host "Por seguranca, o token nao sera exibido."
Write-Host "Agora reinicie o backend MYRA para carregar as variaveis e confira GET /telegram/status."
Write-Host "Se o backend estiver rodando em uma janela existente, feche e inicie novamente."
