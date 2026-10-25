# GUIA DE REINSTALACAO — PROJETO MYRA

Guia completo para reinstalar o projeto MYRA em um computador novo (ou apos formatacao).

Versao do guia: 25/09/2026

---

## 📋 PRE-REQUISITOS

### Hardware
- Windows 10/11
- GPU: NVIDIA RTX A2000 Laptop (4 GB VRAM) ou similar
- CPU: Intel i7 ou similar
- RAM: 16 GB
- Espaco em disco: ~30 GB livres

### Software (instalar nesta ordem)

1. **Python 3.14** — https://www.python.org/downloads/
   - Marcar "Add Python to PATH" na instalacao
   - Verificar: `python --version`

2. **Node.js v24** — https://nodejs.org/
   - Baixar versao LTS
   - Verificar: `node --version`

3. **Git** — https://git-scm.com/download/win
   - Verificar: `git --version`

4. **Docker Desktop** — https://www.docker.com/products/docker-desktop/
   - Verificar: `docker --version`
   - Habilitar WSL 2 no Windows

5. **Ollama** — https://ollama.com/download
   - Verificar: `ollama --version`

6. **Visual C++ Redistributable** — https://aka.ms/vs/17/release/vc_redist.x64.exe
   - Necessario para Playwright e CUDA

---

## 📁 ESTRUTURA DE PASTAS

Criar a pasta base: C:\computer-agent\

    C:\computer-agent\
    ├── agent.py                          # Servidor FastAPI + Playwright
    ├── requirements.txt                  # Dependencias Python
    ├── start.ps1                         # Script de inicializacao
    ├── status.ps1                        # Script de verificacao
    ├── abrir_tudo.ps1                    # Sobe tudo
    ├── README.md                         # Documentacao
    ├── GUIA.md                           # Este arquivo
    ├── notes.txt                         # Notas salvas
    ├── venv\                             # Ambiente virtual Python
    ├── workspace\                        # Area restrita do agente
    ├── screenshots\                      # Prints tirados
    ├── chrome_profile\                   # Perfil persistente do Chrome
    ├── llm-eyes\                         # Servidor de visao
    │   └── models\
    │       └── mmproj-F16.gguf           # Vision projector
    └── webui-custom\                     # Customizacao do MYRA
        ├── nginx.conf                    # Config do proxy reverso
        └── Favicons\                     # Favicons e logo
            ├── MYRALOGO.jpeg             # Imagem original
            ├── favicon.png               # (512x512)
            ├── favicon.ico
            ├── favicon.svg
            ├── favicon-96x96.png
            ├── favicon-32x32.png
            ├── favicon-16x16.png
            ├── apple-touch-icon.png
            ├── logo.png
            └── gerar_favicons_transparente.py

---

## 🐍 PASSO 1 — CONFIGURAR O PYTHON

    cd C:\computer-agent
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    pip install -r requirements.txt
    playwright install chromium

Verificar:
    python --version
    pip list

---

## 🦙 PASSO 2 — CONFIGURAR O OLLAMA

### 2.1 Instalar CUDA v12 (obrigatorio)

A RTX A2000 tem problema com CUDA v13 (crash 0xc0000409). Sempre use CUDA v12.

Variavel permanente (recomendado):
1. Win + R -> sysdm.cpl -> Enter
2. Aba Avancado -> Variaveis de Ambiente
3. Variaveis do usuario -> Novo
4. Nome: OLLAMA_LLM_LIBRARY / Valor: cuda_v12

### 2.2 Baixar modelos

    $env:OLLAMA_LLM_LIBRARY="cuda_v12"
    ollama serve

Em outra janela:
    ollama pull qwen2.5:7b
    ollama pull qwen2.5:3b
    ollama pull gemma2:2b

### 2.3 Verificar

    ollama list

---

## 🐳 PASSO 3 — CONFIGURAR O DOCKER (MYRA)

### 3.1 Baixar a imagem do Open WebUI

    docker pull ghcr.io/open-webui/open-webui:main

### 3.2 Criar o container do MYRA

    docker run -d --name open-webui-custom -p 8080:8080 -e "WEBUI_NAME=MYRA" -e "OLLAMA_BASE_URL=http://host.docker.internal:11434" -e "WEBUI_SECRET_KEY=computer-agent-secret-key-2026" -v open-webui:/app/backend/data --restart unless-stopped ghcr.io/open-webui/open-webui:main

IMPORTANTE: o volume open-webui guarda TODOS os dados (conversas, usuarios, configuracoes). NUNCA remova esse volume.

### 3.3 Criar o proxy Nginx (myra-proxy)

    docker run -d --name myra-proxy -p 8082:80 -v C:\computer-agent\webui-custom\nginx.conf:/etc/nginx/conf.d/default.conf -v C:\computer-agent\webui-custom\Favicons:/usr/share/nginx/html --link open-webui-custom:open-webui-custom --restart unless-stopped nginx:alpine

### 3.4 Verificar

    docker ps

Deve mostrar:
- open-webui-custom na porta 8080
- myra-proxy na porta 8082

Acesse: http://localhost:8082

---

## 🎨 PASSO 4 — CONFIGURAR FAVICONS DO MYRA

### 4.1 Gerar os favicons

    cd C:\computer-agent
    .\venv\Scripts\Activate.ps1
    pip install pillow
    python C:\computer-agent\webui-custom\Favicons\gerar_favicons_transparente.py
    docker restart myra-proxy

---

## 👁️ PASSO 5 — CONFIGURAR O LLM-EYES (VISAO)

### 5.1 Baixar o modelo de visao

O modelo Qwen3.5-0.8B-UD-Q4_K_XL.gguf (~1 GB) fica em:
C:\Users\<SEU_USUARIO>\.cache\huggingface\hub\models--unsloth--Qwen3.5-0.8B-GGUF\

Se nao tiver, baixe do HuggingFace: https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF

### 5.2 Baixar o vision projector

O arquivo mmproj-F16.gguf (~205 MB) fica em:
C:\computer-agent\llm-eyes\models\mmproj-F16.gguf

### 5.3 Iniciar o servidor

    llama-server -m "C:\Users\<SEU_USUARIO>\.cache\huggingface\hub\models--unsloth--Qwen3.5-0.8B-GGUF\snapshots\6ab461498e2023f6e3c1baea90a8f0fe38ab64d0\Qwen3.5-0.8B-UD-Q4_K_XL.gguf" --mmproj "C:\computer-agent\llm-eyes\models\mmproj-F16.gguf" -ngl 99 --host 0.0.0.0 --port 8081

Substitua <SEU_USUARIO> pelo seu nome de usuario do Windows.

---

## 🖥️ PASSO 6 — CONFIGURAR O AGENT.PY

### 6.1 Configurar variaveis de ambiente (Gmail)

1. Ativar 2FA na conta Google
2. Gerar senha de app: https://myaccount.google.com/apppasswords
3. Definir variaveis permanentes:

    [System.Environment]::SetEnvironmentVariable("GMAIL_USER", "seuemail@gmail.com", "User")
    [System.Environment]::SetEnvironmentVariable("GMAIL_APP_PASSWORD", "senha16caracteres", "User")

### 6.2 Iniciar o Uvicorn

    cd C:\computer-agent
    .\venv\Scripts\Activate.ps1
    $env:GMAIL_USER = [System.Environment]::GetEnvironmentVariable('GMAIL_USER', 'User')
    $env:GMAIL_APP_PASSWORD = [System.Environment]::GetEnvironmentVariable('GMAIL_APP_PASSWORD', 'User')
    uvicorn agent:app --host 127.0.0.1 --port 8000

### 6.3 Verificar

Abra http://127.0.0.1:8000/ - deve retornar {"status": "online", "agent": "computer-agent"}

---

## 🤖 PASSO 7 — CONFIGURAR O MYRA (LOCAL AGENT)

### 7.1 Acessar o MYRA

Abra http://localhost:8082 no navegador.

### 7.2 Configurar conexao do Ollama

1. Admin Settings -> Connections
2. Adicionar: http://host.docker.internal:11434
3. Save
4. Verificar se os modelos aparecem

### 7.3 Criar a Tool "BrowserAgent"

1. Admin Settings -> Tools -> + New Tool
2. Colar o codigo da Tool BrowserAgent (27 metodos)
3. Save

### 7.4 Criar o modelo "Local Agent"

1. Workspace -> Models -> + New Model
2. Base Model: qwen2.5:7b
3. Function Calling: Native
4. max_tokens: 2048
5. num_ctx (Ollama): 8192
6. Tool: BrowserAgent (marcar)
7. System Prompt: colar o prompt completo
8. Save

---

## ✅ PASSO 8 — VERIFICAR TUDO

### Checklist

- [ ] Ollama rodando
- [ ] Container open-webui-custom rodando
- [ ] Container myra-proxy rodando
- [ ] llm-eyes rodando
- [ ] agent.py rodando
- [ ] MYRA acessivel em http://localhost:8082
- [ ] MYRA mostra o nome "MYRA"
- [ ] MYRA mostra o favicon correto
- [ ] Modelos do Ollama aparecem no MYRA
- [ ] Tool BrowserAgent esta criada
- [ ] Local Agent esta configurado
- [ ] Chat de teste funciona

---

## 🚀 PASSO 9 — INICIAR TUDO COM UM COMANDO

O script verifica a API do Ollama e inicia `ollama serve` se o servidor local estiver parado; depois sobe backend e widget.

    cd C:\computer-agent
    .\abrir_tudo.ps1

---

## 🐛 SOLUCAO DE PROBLEMAS

### "CUDA error: shared object initialization failed"
Voce esqueceu OLLAMA_LLM_LIBRARY=cuda_v12.

### "agent.py inacessivel" no chat do MYRA
O Uvicorn caiu. Reinicie.

### "Conexao perdida. Reconectando..." no MYRA
O WebSocket nao esta funcionando. Verifique o nginx.conf.

### "Os modelos sumiram do MYRA"
O Ollama foi reiniciado. Va em Admin Settings -> Connections e clique em refresh.

### O titulo do MYRA volta a mostrar "(Open WebUI)"
Cache do navegador. Aperte Ctrl + Shift + R.

### O favicon nao muda
Cache do navegador. Abra em janela anonima.

### Chromium nao abre
Feche todos os Chromium abertos.

### "Porta 8082 ja em uso"
    netstat -ano | findstr ":8082"

---

## 📦 MODELOS INSTALADOS (referencia)

| Modelo | Tamanho | Uso |
|---|---|---|
| qwen2.5:7b | ~4.7 GB | Local Agent (recomendado) |
| qwen2.5:3b | ~1.9 GB | Fallback |
| llama3.1:8b | ~4.9 GB | NAO usar |
| gemma2:2b | ~1.6 GB | Testes |

---

## 🔗 LINKS UTEIS

- Open WebUI: https://docs.openwebui.com/
- Ollama: https://ollama.com/
- Playwright: https://playwright.dev/python/
- FastAPI: https://fastapi.tiangolo.com/
- llama.cpp: https://github.com/ggerganov/llama.cpp

---

## 📅 HISTORICO

- 23/09/2026 — Construcao inicial do agent.py
- 24/09/2026 — Email (IMAP/SMTP), arquivos, web search, visao
- 25/09/2026 — MYRA (Open WebUI customizado), FASE 15 (arquivos avancados), FASE 8 (confirmacao robusta)

---

## 🎯 PROXIMAS FASES

- FASE 18: Criar/Marcar/mover/apagar emails
- FASE 14: TTS + Whisper (voz)
- FASE 10: Apagar chats em lote
- FASE 16: Automacao do PC (run_command)
