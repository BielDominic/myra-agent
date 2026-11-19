# MYRA — instalação no Windows

## Requisitos

- Windows 10/11 x64
- Python 3.14 instalado
- Ollama instalado para inferência local
- Conexão com a internet durante a instalação inicial das dependências Python

## Instalação

1. Baixe e execute MYRA_*_x64-setup.exe na página Releases do GitHub.
2. Abra a pasta de instalação do MYRA (onde estão myra-widget.exe e setup_backend.ps1) e execute setup_backend.ps1 com PowerShell. O script copia o backend para %LOCALAPPDATA%\MYRA\backend, cria um ambiente virtual e instala requirements.txt.
3. Abra MYRA pelo menu Iniciar (atalho criado pelo setup).
4. Carregue a extensão de navegador em chrome://extensions → Modo do desenvolvedor → Carregar sem compactação → selecione %LOCALAPPDATA%\MYRA\backend\browser-extension.

O instalador inclui a interface desktop e os arquivos do backend. O primeiro setup instala as dependências Python localmente; os modelos Ollama e credenciais de serviços externos não são incluídos.

## Dados e privacidade

O processamento do agente é local. Conectores, APIs e sites externos só recebem dados quando uma ação os utiliza. Não distribua sua pasta .env, tokens ou perfis do navegador.

## Diagnóstico

- Backend: http://127.0.0.1:8000
- Logs: %LOCALAPPDATA%\MYRA\logs
- Se o backend não iniciar, consulte backend-stderr.log.
