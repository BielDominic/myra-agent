# MYRA - Instalacao com um clique (Windows)

## Requisitos

- Windows 10/11 x64
- Python 3.14 instalado e disponivel no PATH
- Internet durante a primeira instalacao das dependencias Python
- Ollama instalado para inferencia local (pode ser instalado depois)

## Instalacao

1. Entre na pagina [MYRA Releases](https://github.com/BielDominic/myra-agent/releases).
2. Baixe apenas MYRA_0.26.0_x64-setup.exe.
3. Execute o instalador e conclua as etapas.
4. O instalador copia o backend e executa automaticamente o setup local. Ele cria o ambiente virtual, instala as dependencias e cria o atalho MYRA no menu Iniciar.
5. Abra MYRA pelo menu Iniciar.

Nao e necessario baixar o ZIP complementar nem executar PowerShell manualmente na instalacao normal. O ZIP de backend continua publicado apenas como pacote de recuperacao/instalacao manual.

## O que o instalador faz

- Instala a interface desktop Tauri.
- Copia o backend FastAPI, ferramentas, tarefas e extensao do navegador.
- Executa o setup do Python 3.14 e instala requirements.
- Cria as pastas locais de logs, workspace, perfil do Chrome e screenshots.
- Cria o atalho MYRA no menu Iniciar.

## Integracoes opcionais

- Ollama e os pesos dos modelos nao sao incluidos no instalador.
- GitHub CLI e Git sao opcionais; a sincronizacao com o repositorio privado requer uma conta autorizada.
- Para ativar a extensao do Chrome, abra chrome://extensions, ative o Modo do desenvolvedor e carregue a pasta browser-extension instalada em %LOCALAPPDATA%\MYRA\backend\browser-extension.

## Dados e privacidade

O processamento principal do agente e local. Conectores, APIs e sites externos so recebem dados quando uma acao os utiliza. Nao distribua arquivos .env, tokens ou perfis do navegador.

## Diagnostico

- Backend: http://127.0.0.1:8000
- Logs: %LOCALAPPDATA%\MYRA\logs
- Se o setup automatico falhar, execute %LOCALAPPDATA%\MYRA\backend\venv\Scripts\python.exe para validar o ambiente e consulte os logs de instalacao.
