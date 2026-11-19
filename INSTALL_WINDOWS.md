# MYRA - Instalacao no Windows

## Requisitos

- Windows 10/11 x64
- Python 3.14 instalado
- Ollama instalado para inferencia local
- Conexao com a internet durante a instalacao inicial das dependencias Python

## Instalacao

1. Na pagina Releases do GitHub, baixe os dois arquivos: `MYRA_0.25.0_x64-setup.exe` e `MYRA_v0.25.0_Backend_Setup.zip`.
2. Execute `MYRA_0.25.0_x64-setup.exe` e conclua a instalacao da interface desktop.
3. Extraia o ZIP `MYRA_v0.25.0_Backend_Setup.zip` para uma pasta. A pasta `backend` deve permanecer ao lado de `setup_backend.ps1`.
4. Abra o PowerShell nessa pasta extraida e execute `./setup_backend.ps1`. O script copia o backend para `%LOCALAPPDATA%\MYRA\backend`, cria o ambiente virtual Python, instala as dependencias e cria o atalho no menu Iniciar.
5. Abra MYRA pelo menu Iniciar.
6. Para ativar a extensao do Chrome, abra `chrome://extensions`, ative o Modo do desenvolvedor, selecione Carregar sem compactacao e escolha `%LOCALAPPDATA%\MYRA\backend\browser-extension`.

O primeiro setup pode levar alguns minutos. O instalador nao inclui modelos Ollama nem credenciais de servicos externos.

## Integracao GitHub

A sincronizacao com o repositorio requer Git e GitHub CLI. Para repositorios privados, autentique uma conta que tenha acesso ao repositorio usando `gh auth login`. Se a clonagem nao estiver disponivel, o backend continua instalado; apenas a sincronizacao GitHub fica desativada ate conectar um repositorio.

## Dados e privacidade

O processamento principal do agente e local. Conectores, APIs e sites externos so recebem dados quando uma acao os utiliza. Nao distribua sua pasta `.env`, tokens ou perfis do navegador.

## Diagnostico

- Backend: `http://127.0.0.1:8000`
- Logs: `%LOCALAPPDATA%\MYRA\logs`
- Se o backend nao iniciar, consulte `backend-stderr.log`.
