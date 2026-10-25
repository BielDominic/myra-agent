# Configura o token da API remota da MYRA no ambiente do usuario Windows.
# O token e mostrado apenas uma vez; guarde-o num gestor de senhas antes de fechar a janela.
[CmdletBinding()]
param(
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$current = [Environment]::GetEnvironmentVariable('MYRA_REMOTE_API_TOKEN', 'User')
if ($current -and -not $Force) {
    Write-Host 'Ja existe um token remoto no ambiente do usuario.'
    $answer = Read-Host 'Gerar um token novo e invalidar o anterior? Digite SIM para confirmar'
    if ($answer -cne 'SIM') {
        Write-Host 'Nenhuma alteracao realizada.'
        exit 0
    }
}

$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try {
    $bytes = New-Object byte[] 32
    $rng.GetBytes($bytes)
    $token = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}
finally {
    $rng.Dispose()
}

[Environment]::SetEnvironmentVariable('MYRA_REMOTE_API_TOKEN', $token, 'User')
Write-Host ''
Write-Host 'Token MYRA remoto criado e salvo no ambiente do usuario.' -ForegroundColor Green
Write-Host 'COPIE AGORA O TOKEN ABAIXO PARA UM GESTOR DE SENHAS. Ele nao sera exibido novamente:' -ForegroundColor Yellow
Write-Host $token
Write-Host ''
Write-Host 'Reinicie completamente o backend MYRA para carregar o token.'
Write-Host 'A API remota permanece desativada no processo atual ate o backend ser reiniciado.'
Write-Host 'Nao compartilhe este token nem o grave em arquivos do repositorio.'
