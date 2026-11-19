# Refresh MYRA's configured per-user environment before starting child processes.
# Values are never printed; user-scope settings are the source of truth.
$ErrorActionPreference = "Stop"
$names = @(
    "MYRA_BROWSER_BRIDGE_TOKEN",
    "MYRA_REA_ALLOWED_ROOTS",
    "MYRA_REMOTE_API_TOKEN",
    "MYRA_TELEGRAM_ALLOWED_CHAT_IDS",
    "MYRA_TELEGRAM_BOT_TOKEN",
    "MYRA_CORS_ORIGINS",
    "OLLAMA_HOST",
    "OLLAMA_LLM_LIBRARY",
    "OPENWEBUI_API_KEY"
)
foreach ($name in $names) {
    $value = [Environment]::GetEnvironmentVariable($name, "User")
    [Environment]::SetEnvironmentVariable($name, $value, "Process")
}
Write-Host "Configuracao de ambiente por usuario carregada sem exibir segredos." -ForegroundColor Green
