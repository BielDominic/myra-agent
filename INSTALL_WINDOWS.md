# MYRA - Instalação com um clique (Windows)

## Requisitos
- Windows 10/11 x64.
- Internet é necessária para integrações externas e para o download opcional do Ollama/modelo. O runtime Python, dependências core, ML/visão e Chromium já vêm no instalador.
- Espaço livre recomendado: 8 GB para o aplicativo e ambiente; mais espaço para modelos locais.

## Instalação
1. Abra [MYRA Releases](https://github.com/BielDominic/myra-agent/releases).
2. Baixe `MYRA_0.26.2_x64-setup.exe`.
3. Execute o instalador. Ele instala o aplicativo e prepara o backend do seu usuário.
4. O assistente final pergunta se deseja instalar o Ollama e baixar um modelo local. A opção vem marcada por padrão, mas pode ser desmarcada ou adiada.
5. Abra MYRA pelo menu Iniciar.

## Componentes incluídos
- Python oficial 3.14.10 x64.
- Wheels offline fixadas do backend: FastAPI, Uvicorn, Pydantic, Playwright, Requests, Pillow, psutil, PyYAML, Jinja2, yt-dlp, YouTube Transcript API, PyAutoGUI, PyGetWindow, pywinauto, MSS, keyboard e pywebview.
- Stack CPU de ML/visão: NumPy, OpenCV, ONNX Runtime, RapidOCR, PyTorch CPU, TorchVision, Ultralytics e dependências transitivas.
- Chromium compatível com Playwright.
- Backend, ferramentas, tarefas, extensão Chrome e scripts de inicialização.
- O instalador prepara os ambientes Python offline, sem PyPI.

## Ollama e modelo local (escolha do usuário)
O assistente oferece instalar o Ollama via Windows Package Manager e baixar um modelo inicial. O modelo padrão é `qwen2.5:3b`; também é possível escolher `qwen2.5:7b`, `llama3.2:3b` ou `qwen2.5:1.5b`. O download do modelo requer internet e pode consumir de cerca de 1 GB a vários GB, dependendo da escolha. O usuário pode pular e configurar depois.

Os pesos do modelo **não estão dentro do EXE**: são baixados pelo Ollama para evitar duplicar vários gigabytes em cada cópia do instalador. O PyTorch incluído é CPU-only para funcionar em computadores com diferentes GPUs; aceleração CUDA é uma opção futura separada.

## Espaço de trabalho por usuário
Cada conta do Windows tem seus próprios dados em `%LOCALAPPDATA%\MYRA`, incluindo:
- `workspace\projects`
- `workspace\downloads`
- `workspace\artifacts`
- `workspace\memory`
- `chrome_profile`
- `config\user_profile.json`
- `config\model.json` (quando um modelo é configurado)

Os dados não são compartilhados entre contas Windows diferentes. O instalador não conecta o usuário ao computador do desenvolvedor nem envia o workspace ao GitHub.

## Extensão Chrome
Abra `chrome://extensions`, ative o Modo do desenvolvedor e carregue a pasta `browser-extension` em `%LOCALAPPDATA%\MYRA\backend\browser-extension`.

## Diagnóstico
- Backend: http://127.0.0.1:8000
- Logs: `%LOCALAPPDATA%\MYRA\logs`
- Reexecute `%LOCALAPPDATA%\MYRA\setup_backend.ps1` para reparar o ambiente.
- Para configurar o Ollama/modelo depois: `%LOCALAPPDATA%\MYRA\setup_models.ps1`.
