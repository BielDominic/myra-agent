# 📄 README.md — atualizado com o estado atual

Antes de commitar, vamos atualizar o README pra refletir tudo que a MYRA é **hoje**. Vou fazer uma versão limpa, profissional e completa.

**Abre o arquivo:**

```powershell
notepad C:\computer-agent\README.md
```

Se quiser fazer backup antes:

```powershell
Copy-Item C:\computer-agent\README.md C:\computer-agent\README_backup.md -Force
```

Cola o conteúdo abaixo (substitui tudo), salva em **UTF-8**:

---

```markdown
# 🤖 MYRA — Agente de Computador Local

**Um agente de IA que roda 100% na sua máquina, 100% grátis, com controle total sobre o computador.**

MYRA (antes "Computer Agent") é uma IA pessoal capaz de navegar na internet, controlar o PC, ler/escrever arquivos, gerenciar emails, programar, transcrever vídeos e — desde a FASE 24 — **planejar e executar tarefas de forma autônoma**, decidindo passo a passo qual ferramenta usar.

---

## ✨ O QUE A MYRA FAZ HOJE

### 🧠 Autonomia (o coração)
- **Planeja** tarefas sozinha: você descreve o objetivo, ela decide os passos
- **Encadeia** ferramentas: busca web → abre site → lê → resume
- **Adapta**: se uma ferramenta falha, tenta outra abordagem
- **Sintetiza** respostas em português, fiéis ao conteúdo real
- **Retry** automático em caso de erro

### 🌐 Navegador (Playwright + Chrome real)
- Abre URLs, pesquisa Google/DuckDuckGo
- Clica por texto, descrição ou seletor
- Digita em campos (detecta email, senha, usuário)
- Lê páginas (estruturado ou texto solto)
- Tira screenshots
- Perfil persistente (login uma vez, mantém sessão)

### 🎬 YouTube
- Transcrição automática com **detecção de idioma** (pt > en > outros)
- Prioriza legenda manual sobre auto-gerada
- Resumo, perguntas, salvar, listar, ler
- Correção automática de encoding (VTT duplo)

### 📧 Email (Gmail IMAP/SMTP)
- Lista, lê, busca, marca lido/não lido
- Envia, responde, move, deleta
- Delete em massa por termo ("apague 5 emails do LinkedIn")
- **Confirmação** antes de ações destrutivas

### 📂 Arquivos (workspace)
- Lista, lê, escreve, cria, move, deleta
- Busca texto em múltiplos arquivos
- Acesso restrito ao `workspace/` (segurança)

### 💻 Coding Agent (21 ferramentas)
- Gera, explica, analisa, refatora, otimiza, converte código
- Code review, lint, métricas, dependências
- Testes, documentação, SQL, regex, scaffold
- Executa código (Python) e interpreta output

### 🖥️ Controle do PC
- Mouse: move, clique, duplo clique, clique direito, scroll
- Teclado: digita, pressiona tecla, combina teclas (Ctrl+C, Alt+Tab, Win+D)
- Janelas: lista, foca, pega ativa
- Screenshots do desktop

### 👁️ Visão
- Vê a tela via Qwen3.5-0.8B (llama-server local)
- Responde perguntas sobre o que está vendo

### 🌦️ Info do mundo
- Clima (Open-Meteo)
- Hora/data
- Web search estruturado (links + snippets)
- YouTube search

### 📊 Gráficos e dados
- Plotly: gráficos, tabelas, heatmaps, timelines (Visuals Core)

### 💬 Gerenciamento de chats
- Lista, renomeia, deleta chats (individual ou por busca)

### 🌐 Ferramentas estruturadas (novo!)
- `search_google_structured` → lista de links
- `web_search_structured` → lista de links
- `youtube_search` → lista de vídeos
- `youtube_channel_latest` → últimos vídeos de um canal
- `get_current_url` → URL atual do navegador
- `read_page_structured` → texto + links + botões + inputs

---

## 🏗️ ARQUITETURA

```
┌──────────────────────────────────────────────────┐
│         Open WebUI (Docker, porta 8080)          │
│         Interface do chat (customizado MYRA)     │
└─────────────────────┬────────────────────────────┘
                      │ HTTP
                      ▼
┌──────────────────────────────────────────────────┐
│         agent.py (FastAPI, porta 8000)           │
│         ~95 rotas, coração do sistema            │
└──┬───────────────────────────────────────────┬───┘
   │                                           │
   │ Planejador + Loop adaptativo              │ Ações
   │ (Ollama, porta 11434)                     │
   ▼                                           ▼
┌────────────────────┐              ┌─────────────────────┐
│ tasks/             │              │ Navegador (Chrome)  │
│ - simple_task.py   │              │ Sistema de arquivos │
│ - structured_tools │              │ Email (Gmail)       │
│   (loop + 6 tools) │              │ PC (mouse/teclado)  │
└────────────────────┘              │ Visão (llama-server)│
                                    └─────────────────────┘
```

### 🧩 Componentes principais

| Componente | Papel |
|---|---|
| **`agent.py`** | Servidor FastAPI com ~95 rotas (navegador, email, PC, YouTube, code, task) |
| **`tasks/simple_task.py`** | Loop de autonomia adaptativo (LLM decide 1 passo por vez) |
| **`tasks/structured_tools.py`** | 6 ferramentas que devolvem JSON (busca, YouTube, etc.) |
| **`tools/browseragent.py`** | Tool do Open WebUI (expõe rotas do agent pro chat) |
| **`tools/codeagent.py`** | Tool do Open WebUI (21 ferramentas de programação) |
| **`tools/visuals_core.py`** | Tool do Open WebUI (gráficos) |
| **`computer/`** | Módulo de automação do PC (mouse, teclado, janelas, tela) |

---

## 🔧 INFRAESTRUTURA

### Serviços rodando localmente

| Serviço | Porta | O que faz |
|---|---|---|
| **agent.py (FastAPI)** | 8000 | Servidor principal |
| **Open WebUI (Docker)** | 8080 | Interface do chat |
| **nginx proxy** | 8082 | Troca "Open WebUI" por "MYRA" |
| **Ollama** | 11434 | LLM (qwen2.5:7b, llama3.1:8b, coders) |
| **llama-server (visão)** | 8081 | Qwen3.5-0.8B para ver a tela |

### Modelos Ollama

| Modelo | Uso |
|---|---|
| **`qwen2.5:7b`** | Modelo principal do chat (tool calling nativo) |
| **`llama3.1:8b`** | Alternativo (tool calling mais robusto) |
| **`qwen3.5:4b`** | Com visão |
| **`R4C3R/qwen2.5-coder-3b-heretic`** | CodeAgent primário (sem censura) |
| **`qwen2.5-coder:7b`** | CodeAgent fallback |
| **`Qwen3.5-0.8B + mmproj`** | Visão (via llama-server) |

### Hardware

- **SO:** Windows 11
- **GPU:** RTX A2000 Laptop (4 GB VRAM)
- **CPU:** i7-11850H
- **RAM:** 16 GB

---

## 🚀 COMO USAR

### Iniciar tudo

**Terminal 1 — Agent:**
```powershell
cd C:\computer-agent
.\venv\Scripts\python.exe agent.py
```

**Terminal 2 — Visão (opcional, só se usar `see_image`):**
```powershell
C:\computer-agent\iniciar_visao.ps1
```

**Docker (Open WebUI):**
```powershell
docker start open-webui-custom
```

### Usar no chat

Abre **http://127.0.0.1:8080** (ou `:8082` pelo proxy) no navegador:

- **Modelo:** `qwen2.5:7b`
- **Tool:** BrowserAgent ativada

**Exemplos de comandos:**

```
Use task_run com o objetivo exato: "que horas sao agora?"

Use task_run com o objetivo exato: "pesquise os melhores cursos de IA em Dublin e diga 3 nomes"

Use task_run com o objetivo exato: "pesquise o canal do Post Malone no YouTube, ache o ultimo video dele e me diga o titulo"

Use task_run com o objetivo exato: "resuma o video https://www.youtube.com/watch?v=m226f2reF28"
```

### Usar direto na API

```powershell
# Task autônoma
$body = @{ objetivo = "pesquise X"; max_passos = 15 } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/task_simple" -Method Post -Body $body -ContentType "application/json"

# Ferramenta específica
$body = @{ url = "https://youtu.be/..." } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/youtube_transcript" -Method Post -Body $body -ContentType "application/json"
```

---

## 📁 ESTRUTURA DE PASTAS

```
C:\computer-agent\
├── agent.py                    # Servidor FastAPI (~95 rotas)
├── agent_backup_*.py           # Backups
├── iniciar_myra.ps1            # Sobe o agent.py
├── iniciar_visao.ps1           # Sobe o llama-server (visão)
├── REINSTALACAO.md             # Guia completo de reinstalação
├── README.md                   # Este arquivo
├── ROADMAP.md                  # Planejamento (~230 itens)
├── CONTEXTO.txt                # Estado atual
├── .gitignore                  # Ignora venv, backups, screenshots
│
├── tasks/                      # Núcleo do agente autônomo
│   ├── __init__.py
│   ├── simple_task.py          # Loop adaptativo (LLM decide passo a passo)
│   └── structured_tools.py     # 6 ferramentas JSON (busca, YouTube, etc.)
│
├── tools/                      # Tools do Open WebUI (versionadas)
│   ├── browseragent.py         # Tool principal (~50 métodos)
│   ├── codeagent.py            # 21 métodos de programação
│   ├── visuals_core.py         # 10 métodos de gráficos
│   ├── README.md
│   └── upload/upload_tools.ps1
│
├── computer/                   # Automação do PC
│   ├── controller.py           # Mouse/teclado (pyautogui)
│   ├── screen.py               # Screenshot (mss)
│   └── windows.py              # Janelas (pygetwindow + ctypes)
│
├── workspace/                  # Área segura de trabalho
│   ├── code/                   # Código gerado pelo CodeAgent
│   └── youtube/                # Transcrições salvas
│
├── screenshots/                # Prints
├── chrome_profile/             # Perfil dedicado do Chrome
├── venv/                       # Ambiente virtual Python 3.14
│
└── llm-eyes/                   # Modelo de visão
    └── models/
        ├── Qwen3.5-0.8B-UD-Q4_K_XL.gguf
        └── mmproj-F16.gguf
```

---

## 📊 FASES DO PROJETO

### ✅ Concluídas

- **FASE 0-10** — Base: navegador, email, arquivos, chats, confirmação
- **FASE 15** — Mais ferramentas de arquivo
- **FASE 16** — Automação do PC (mouse, teclado, janelas)
- **FASE 17** — CodeAgent (21 ferramentas)
- **FASE 18-19** — Melhorias incrementais
- **FASE 20** — YouTube (transcrição, resumo, perguntas)
- **FASE 20.1** — Detecção automática de idioma do YouTube
- **FASE 22-light** — Task simples (planner + loop + retry)
- **FASE 24.1** — Loop de autonomia adaptativo ⭐
- **FASE 24.2** — Ferramentas estruturadas (6 novas) ⭐

### 🚧 Próximas

- **FASE 22.5** — Polir o `responder` (respostas diretas)
- **FASE 34** — Bot do Telegram (controle remoto)
- **FASE 24.3** — Recuperação de erros no loop
- **FASE 24.4** — Verificação visual
- **FASE 24.5** — Persistência SQLite

### 📅 Médio prazo

- **FASE 14** — TTS + Whisper (MYRA fala e ouve)
- **FASE 20.5** — Whisper (transcrição de áudio de vídeos sem legenda)
- **FASE 12** — Geração de imagem
- **FASE 31** — Scheduler (tarefas agendadas)
- **FASE 32** — Notificações (Windows, Telegram, voz)
- **FASE 33** — Memória de longo prazo

Ver **[ROADMAP.md](ROADMAP.md)** para lista completa (~230 itens).

---

## 🔐 SEGURANÇA

- **Workspace isolado**: arquivos só em `workspace/`
- **Confirmação dupla** em ações destrutivas (delete, move, email)
- **Perfil dedicado do Chrome** (não mexe no seu navegador pessoal)
- **API key do Open WebUI** em variável de ambiente
- **Nada sai da sua máquina** — tudo local

---

## 🎓 APRENDIZADOS IMPORTANTES

### ⚠️ Regras críticas

1. **NUNCA editar `agent.py` via `Set-Content`, `-replace` ou `WriteAllText` do PowerShell** — trunca o arquivo. **Sempre** usar Notepad ou VSCode.
2. **Sempre fazer backup** antes de grandes mudanças:
   ```powershell
   Copy-Item C:\computer-agent\agent.py C:\computer-agent\agent_backup_YYYYMMDD.py -Force
   ```
3. **Encoding:** sempre **UTF-8** ao salvar arquivos Python.
4. **Após editar `agent.py`:** rodar `python -m py_compile C:\computer-agent\agent.py`.
5. **Após editar Tool no Open WebUI:** `docker restart open-webui-custom`.
6. **Após editar `agent.py`:** `Ctrl+C` na Janela 1 e `iniciar_myra.ps1`.

### 🐛 Bugs conhecidos e suas soluções

| Bug | Sintoma | Solução |
|---|---|---|
| **PowerShell 5.1 + UTF-8** | `MÃºsica` em vez de `Música` na tela | Bug visual. Usar `curl.exe -o arquivo` e ler com UTF-8 |
| **urllib no FastAPI** | `getaddrinfo failed` | Usar `requests` em vez de `urllib.request` |
| **Post Malone no YouTube** | Handle `@Post Malone` (com espaço) dá 404 | Normalizar handle (lowercase, sem espaço) |
| **LLM chama mesma ferramenta 2x** | Loop redundante | Limitação do `qwen2.5:7b`, ajustar prompt |

### 🎯 Arquitetura de decisão

Quando o LLM precisa escolher entre ferramentas parecidas:

- **`web_search`** (antigo) → texto solto, difícil de parsear
- **`web_search_structured`** (novo) → JSON, fácil de encadear ✅
- **`search_google`** (antigo) → só confirma "pesquisei"
- **`search_google_structured`** (novo) → lista de links ✅
- **`youtube_transcript`** → transcrição de UM vídeo
- **`youtube_search`** → achar um vídeo por termo
- **`youtube_channel_latest`** → últimos vídeos de um canal

**Regra:** sempre preferir as ferramentas `_structured` em tarefas autônomas.

---

## 🧪 TESTES DE VALIDAÇÃO

### Verificar se tá tudo rodando

```powershell
# Agent
curl.exe -s http://127.0.0.1:8000/

# Open WebUI
docker ps --filter name=open-webui-custom --format "{{.Names}} {{.Status}}"

# Ollama
curl.exe -s http://127.0.0.1:11434/api/tags | findstr qwen2.5

# Visão
curl.exe -s http://127.0.0.1:8081/v1/models
```

### Testar o agente autônomo

```powershell
# Teste simples (1-2 passos)
$body = @{ objetivo = "que horas sao agora?"; max_passos = 15 } | ConvertTo-Json
$r = Invoke-RestMethod -Uri "http://127.0.0.1:8000/task_simple" -Method Post -Body $body -ContentType "application/json"
$r.status
$r.historico | ForEach-Object { "  $($_.passo): $($_.ferramenta) - ok=$($_.ok)" }
$r.resultado_final

# Teste multi-passo (Post Malone)
$body = @{ objetivo = "pesquise o canal do Post Malone no YouTube, ache o ultimo video dele e me diga o titulo"; max_passos = 15 } | ConvertTo-Json
$r = Invoke-RestMethod -Uri "http://127.0.0.1:8000/task_simple" -Method Post -Body $body -ContentType "application/json"
$r.status
$r.historico | ForEach-Object { "  $($_.passo): $($_.ferramenta)" }
$r.resultado_final
```

---

## 📚 REPOSITÓRIO

- **URL:** https://github.com/BielDominic/myra-agent
- **Branch principal:** `main`
- **Último commit:** `feat: FASE 24 - loop de autonomia real + ferramentas estruturadas`

---

## 🎯 FILOSOFIA

**MYRA = cérebro + olhos + mãos + memória + autonomia.**

- **Cérebro:** LLM local (Ollama)
- **Olhos:** Visão (llama-server + Qwen3.5-0.8B) + screenshots
- **Mãos:** Navegador + controle do PC + arquivos + email
- **Memória:** Notas + histórico + (futuro) SQLite
- **Autonomia:** Loop adaptativo (FASE 24)

**Regra de ouro:** escolher a ferramenta **mais específica** pro trabalho.
API → DOM → filesystem → vision → computer control.

**Regra crítica:** **nunca editar arquivos grandes via PowerShell direto.**

---

## 🙏 CRÉDITOS

- **Playwright** (navegador)
- **FastAPI** (servidor)
- **Ollama** (LLM local)
- **Open WebUI** (interface)
- **yt-dlp** (YouTube)
- **pyautogui** + **mss** + **pygetwindow** (automação do PC)

---

**MYRA é uma IA pessoal de verdade.** Feita para rodar local, sem depender de APIs pagas, com controle total sobre o computador.

🚀 **Let's go.**
```

---

## 🛠️ Como aplicar

1. **Backup** (opcional):
   ```powershell
   Copy-Item C:\computer-agent\README.md C:\computer-agent\README_backup.md -Force
   ```

2. **Abre**:
   ```powershell
   notepad C:\computer-agent\README.md
   ```

3. **Ctrl+A** → **Delete** → **Ctrl+V** (cola o conteúdo acima)

4. **Salva em UTF-8** (Arquivo → Salvar como → Codificação: UTF-8)

5. **Fecha o Notepad**

---

## 📋 Depois disso

**Roda o commit geral (código + README):**

```powershell
cd C:\computer-agent
git status
git add agent.py tasks/ README.md ROADMAP.md
git commit -m "feat: FASE 24 + atualiza README e ROADMAP

Código (FASE 24.1 + 24.2):
- tasks/simple_task.py: loop adaptativo (LLM decide 1 passo por vez)
- tasks/structured_tools.py: 6 ferramentas JSON novas
- agent.py: rotas /get_current_url e /read_page_structured
- agent.py: TaskSimple.max_passos default 15

Documentação:
- README.md: reescrito com estado atual, arquitetura, aprendizados
- ROADMAP.md: já estava atualizado

Testado end-to-end:
- 'ache o ultimo video do Post Malone' -> funcionou em 1 passo"

git push
```
