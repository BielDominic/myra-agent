# MYRA - Instalacao com um clique (Windows)

## Requisitos
- Windows 10/11 x64.
- Internet apenas para integrações externas, sincronização GitHub e recursos online; o runtime Python e as dependências principais já vêm no instalador.
- Ollama instalado para inferência local (pode ser instalado depois).

## Instalacao
1. Entre na pagina [MYRA Releases](https://github.com/BielDominic/myra-agent/releases).
2. Baixe MYRA_0.26.1_x64-setup.exe.
3. Execute o instalador e conclua as etapas.
4. O instalador instala o runtime oficial Python 3.14.10 se necessário, cria o ambiente virtual, instala os pacotes a partir do wheelhouse offline e copia o Chromium do Playwright.
5. Abra MYRA pelo menu Iniciar.

Nao e necessario instalar Python, baixar pacotes do PyPI ou executar PowerShell manualmente. O ZIP complementar contém o mesmo payload completo para recuperação/instalação manual.

## Conteudo incluído no instalador
- Runtime oficial Python 3.14.10 x64 (SHA-256 validado durante a preparação do release).
- Dependências principais do backend como wheels offline: FastAPI, Uvicorn, Pydantic, Playwright, Requests, Pillow, psutil, PyYAML, Jinja2, yt-dlp, YouTube Transcript API, PyAutoGUI, PyGetWindow, pywinauto, mss, keyboard e pywebview, incluindo dependências transitivas.
- Navegador Chromium compatível com a versão de Playwright empacotada.
- Backend MYRA, tarefas, módulos de computador, ferramentas e extensão do navegador.
- Scripts de instalação e inicialização.

## Componentes que não fazem parte do pacote base
- Ollama e os pesos dos modelos LLM (downloads independentes, conforme o modelo escolhido).
- Grupo opcional de visão computacional/ML: NumPy, OpenCV, ONNX Runtime, RapidOCR, PyTorch e Ultralytics. Esses pacotes são grandes e devem ser instalados pelo complemento de visão quando necessário.
- Git/GitHub CLI e credenciais de acesso ao repositório privado.
- Chaves de APIs e integrações externas.

## Extensao do Chrome
Abra chrome://extensions, ative o Modo do desenvolvedor e carregue a pasta browser-extension instalada em %LOCALAPPDATA%\MYRA\backend\browser-extension.

## Dados e privacidade
O processamento principal do agente e local. Conectores, APIs e sites externos so recebem dados quando uma acao os utiliza. Nao distribua arquivos .env, tokens ou perfis do navegador.

## Diagnostico
- Backend: http://127.0.0.1:8000
- Logs: %LOCALAPPDATA%\MYRA\logs
- Se o setup automatico falhar, execute %LOCALAPPDATA%\MYRA\setup_backend.ps1 novamente e consulte os logs de instalacao.
