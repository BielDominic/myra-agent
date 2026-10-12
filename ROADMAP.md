# MYRA - Roadmap

[![Progress](https://img.shields.io/badge/Progress-67%25-orange?style=flat-square)]()
[![Active Phase](https://img.shields.io/badge/Active_Phase-25-blue?style=flat-square)]()
[![Phases](https://img.shields.io/badge/Phases-31-purple?style=flat-square)]()
[![Updated](https://img.shields.io/badge/Updated-2026-10-12-lightgrey?style=flat-square)]()
[![Language](https://img.shields.io/badge/Language-PT--BR_%7C_EN-green?style=flat-square)]()

**Documentacao disponivel em:** [Portugues](#portugues) | [English](#english)

---

<a id="portugues"></a>

## Portugues (PT-BR)

### Legenda

| Badge | Significado |
|-------|-------------|
| ![Concluida](https://img.shields.io/badge/-CONCLUIDA-brightgreen?style=flat-square) | Fase 100% pronta |
| ![Em progresso](https://img.shields.io/badge/-EM_PROGRESSO-yellow?style=flat-square) | Sendo trabalhada |
| ![Pendente](https://img.shields.io/badge/-PENDENTE-lightgrey?style=flat-square) | Planejada, nao iniciada |
| ![Bloqueada](https://img.shields.io/badge/-BLOQUEADA-red?style=flat-square) | Depende de outra fase |
| ![Cancelada](https://img.shields.io/badge/-CANCELADA-red?style=flat-square) | Descartada |

### Indice

- [Fases concluidas](#pt-fases-concluidas)
- [Proximas fases](#pt-proximas-fases)
- [Medio prazo](#pt-medio-prazo)
- [Longo prazo](#pt-longo-prazo)
- [Canceladas](#pt-canceladas)
- [Resumo por area](#pt-resumo)

---

<a id="pt-fases-concluidas"></a>

### Fases concluidas

#### Base (FASES 0-10, 15-19)
![Concluida](https://img.shields.io/badge/-CONCLUIDA-brightgreen?style=flat-square)

- [x] Servidor FastAPI (`agent.py`) com ~90 rotas
- [x] Navegador (Playwright): 10 rotas
- [x] Visao (`see_image` via llama-server)
- [x] Email (IMAP/SMTP Gmail): 10 rotas
- [x] Utilitarias: hora, notas, clima, run_python
- [x] Arquivos (workspace): 7 rotas
- [x] Web search (DuckDuckGo)
- [x] Automacao PC (FASE 16): 12 rotas
- [x] Chats (FASE 10): 5 rotas
- [x] CodeAgent (FASE 17): 21 tools
- [x] Sistema de confirmacao de acoes destrutivas

#### YouTube (FASE 20)
![Concluida](https://img.shields.io/badge/-CONCLUIDA-brightgreen?style=flat-square)

- [x] 6 rotas: transcript, summarize, ask, save, list, read
- [x] FASE 20.1 - Deteccao automatica de idioma
- [x] Fix de encoding de VTT

#### Agente autonomo (FASE 22-light)
![Concluida](https://img.shields.io/badge/-CONCLUIDA-brightgreen?style=flat-square)

- [x] `tasks/simple_task.py` - planner + loop + retry
- [x] Rota `/task_simple`
- [x] Integracao com Open WebUI (`task_run`)
- [x] Fix do bug multilingue

#### Autonomia real (FASE 24.1-24.3)
![Concluida](https://img.shields.io/badge/-CONCLUIDA-brightgreen?style=flat-square)

- [x] **24.1** - Loop adaptativo (LLM decide 1 passo por vez)
- [x] **24.2** - Ferramentas estruturadas (6)
- [x] **24.3** - Cancelamento real via flag compartilhada

#### Bridge + Widget (FASE 24.4)
![Concluida](https://img.shields.io/badge/-CONCLUIDA-brightgreen?style=flat-square)

- [x] Extensao Chrome MV3 com 12 ferramentas
- [x] Polling serializado (setTimeout recursivo)
- [x] Widget Tauri com modo pilula/quadrado
- [x] Balao de fala, boca animada, olhos seguindo mouse
- [x] Travar posicao + sempre no topo (separados)
- [x] Configuracoes: tema, compacto, som, DND

#### Infraestrutura
![Concluida](https://img.shields.io/badge/-CONCLUIDA-brightgreen?style=flat-square)

- [x] Ollama com CUDA v12
- [x] Open WebUI em Docker
- [x] nginx proxy com sub_filter
- [x] Scripts `abrir_tudo.ps1`
- [x] Chrome com perfil dedicado
- [x] `OPENWEBUI_API_KEY` em env var

#### Documentacao
![Concluida](https://img.shields.io/badge/-CONCLUIDA-brightgreen?style=flat-square)

- [x] README.md profissional com badges
- [x] HANDOFF.md
- [x] ROADMAP.md (este arquivo)
- [x] .gitignore robusto

---

<a id="pt-proximas-fases"></a>

### Proximas fases

#### FASE 25 - Visao com Coordenadas
![Em progresso](https://img.shields.io/badge/-EM_PROGRESSO-yellow?style=flat-square)

**Meta:** vision_locate(descricao) retorna coordenadas X/Y

- [ ] `/vision_locate(descricao)` - retorna dict com x, y, confidence
- [ ] `/vision_click(descricao)` - localiza + clica
- [ ] `/vision_type(campo_desc, texto)` - localiza + digita
- [ ] Normalizacao de coordenadas (DPI, resolucao)
- [ ] Fallback: OCR via Tesseract
- [ ] Integracao no planner

**Ferramentas free:** llm-eyes (ja tem), Tesseract, OmniParser, UI-TARS

#### FASE 26 - Ciclo Autonomo Completo
![Pendente](https://img.shields.io/badge/-PENDENTE-lightgrey?style=flat-square)

**Meta:** LLM age, observa, verifica, corrige

- [ ] _observar() - screenshot + analise apos cada acao
- [ ] _verificar(objetivo) - check se atingiu
- [ ] _recuperar(erro) - nova estrategia
- [ ] Task persistence (retomar apos crash)
- [ ] Pausa/continua sem perder contexto

#### FASE 27 - Overlay Visual TARS
![Pendente](https://img.shields.io/badge/-PENDENTE-lightgrey?style=flat-square)

**Meta:** ver o cursor animado, highlight, borda ativa

- [ ] Janela Tauri transparente click-through
- [ ] Canal de eventos (SSE /task_events ja existe)
- [ ] Cursor animado
- [ ] Highlight do alvo antes de clicar
- [ ] Estados visuais (observando/pensando/executando)
- [ ] Trajetoria do mouse visivel
- [ ] Cancelamento visual

#### FASE 28 - Controle Mobile
![Pendente](https://img.shields.io/badge/-PENDENTE-lightgrey?style=flat-square)

##### 28.1 - Infra de acesso remoto (Tailscale)
- [ ] Tailscale no PC Windows
- [ ] Tailscale no iPhone
- [ ] IP estavel (100.x.y.z)

##### 28.2 - Telegram Bot
- [ ] Bot no @BotFather
- [ ] Webhook em agent.py
- [ ] Comandos: /task, /status, /cancel, /screenshot, /see
- [ ] Notificacao automatica ao concluir
- [ ] Autenticacao por chat_id

##### 28.3 - App iOS Nativo
- [ ] App shell (Swift/SwiftUI)
- [ ] Tela de chat
- [ ] Widget lock screen
- [ ] Widget home screen
- [ ] Siri Shortcuts
- [ ] Notificacoes APNs

#### FASE 29 - Integracao CarPlay
![Pendente](https://img.shields.io/badge/-PENDENTE-lightgrey?style=flat-square)

**Caminho:** Audio App (aparece como player no CarPlay)

- [ ] Base iOS shell + Tailscale
- [ ] TTS (Piper) + STT (Whisper)
- [ ] CarPlay Audio App framework
- [ ] MPNowPlayingInfoCenter
- [ ] Botoes do volante mapeados
- [ ] Publicacao (opcional: TestFlight)

#### FASE 30 - Distribuicao
![Pendente](https://img.shields.io/badge/-PENDENTE-lightgrey?style=flat-square)

- [ ] cargo tauri build + .exe
- [ ] Instalador NSIS
- [ ] Auto-start no boot
- [ ] Bandeja do sistema
- [ ] Notificacao nativa Windows
- [ ] Indicador de conexao no widget

#### FASE 31 - Interface Propria
![Bloqueada](https://img.shields.io/badge/-BLOQUEADA-red?style=flat-square)

**Bloqueada por:** FASE 27 (overlay) + FASE 30 (distribuicao)

- [ ] Design (Figma)
- [ ] Frontend Svelte/SolidJS
- [ ] WebSocket com agent.py
- [ ] Chat com markdown
- [ ] Painel de tasks em execucao
- [ ] Migracao do Open WebUI

---

<a id="pt-medio-prazo"></a>

### Medio prazo

#### FASE 22.5+ - Polimento do agente
- [ ] Melhorar responder (respostas diretas)
- [ ] Mais ferramentas no task_run
- [ ] Logs estruturados
- [ ] Modo "vou perguntar antes de agir"

#### FASE 24.5 - Persistencia SQLite
- [ ] Tasks sobrevivem a restart
- [ ] Historico consultavel
- [ ] Schema SQLite

#### FASE 14 - Voz e Audio
- [ ] TTS + Whisper
- [ ] Wake word ("MYRA, ...")
- [ ] Conversa por voz continua
- [ ] Escolha de voz

#### FASE 20.5-20.11 - YouTube avancado
- [ ] Whisper pra videos sem legenda
- [ ] Vimeo, outros sites
- [ ] Extrair MP3
- [ ] Baixar video
- [ ] Playlists
- [ ] Cache de transcricoes
- [ ] Vision sobre frames

#### FASE 12 - Geracao de midia
- [ ] Geracao de imagem (API free)
- [ ] Edicao (crop, resize, filtro)
- [ ] Remocao de fundo
- [ ] Upscale
- [ ] OCR

#### FASE 15 - Arquivos avancados
- [ ] Ler PDFs
- [ ] Ler Excel/CSV
- [ ] Ler Word/DOCX
- [ ] Ler PowerPoint
- [ ] Converter formatos
- [ ] Acesso fora do workspace
- [ ] Compactar/descompactar
- [ ] Hash, diff
- [ ] Monitorar pastas

#### Web avancado
- [ ] Baixar arquivos via navegador
- [ ] Formularios multi-step
- [ ] Login automatico
- [ ] Screenshot de elemento
- [ ] Extrair tabelas
- [ ] Detectar CAPTCHA
- [ ] iFrames e shadow DOM
- [ ] Cookies e localStorage
- [ ] Bloquear ads/trackers

#### Computer Use avancado
- [ ] Drag and drop
- [ ] Clipboard
- [ ] Maximizar/minimizar janelas
- [ ] Abrir/fechar apps
- [ ] Processos
- [ ] Popups inesperados
- [ ] Multiplos monitores

#### Vision avancado
- [ ] Modelo maior (Qwen2.5-VL-7B)
- [ ] Identificar botoes
- [ ] Coordenadas de elemento (coberto pela FASE 25)
- [ ] Comparar antes/depois
- [ ] Detectar erro visual
- [ ] OCR embutido
- [ ] Deteccao de CAPTCHA

#### Coding Agent avancado
- [ ] Corrigir bugs automaticamente
- [ ] Rodar projeto inteiro
- [ ] Git via tool
- [ ] Criar projeto completo
- [ ] Analisar projeto
- [ ] Instalar dependencias
- [ ] Rodar testes + interpretar
- [ ] Loop: rodar -> ver erro -> corrigir -> rodar

#### Email avancado
- [ ] Baixar anexos
- [ ] Analisar anexos
- [ ] Encaminhar
- [ ] Criar rascunho
- [ ] Arquivar
- [ ] Detectar prazos
- [ ] Resumir thread

#### Info do mundo
- [ ] Noticias (RSS)
- [ ] Precos (acoes, cripto)
- [ ] Mapas / rotas
- [ ] Traducao
- [ ] Cotacao de moedas
- [ ] Google Calendar
- [ ] Google Contacts
- [ ] RAG em PDFs locais

#### Windows / Sistema
- [ ] Instalar software (winget)
- [ ] Atualizar software
- [ ] Configurar apps
- [ ] Diagnostico
- [ ] Monitorar recursos
- [ ] Backup automatico

#### Terminal
- [ ] Interpretar output
- [ ] PowerShell estruturado
- [ ] CMD estruturado
- [ ] npm/yarn/pnpm
- [ ] pip/poetry/uv
- [ ] Docker
- [ ] Ollama
- [ ] Git
- [ ] Timeout adaptativo
- [ ] Background + polling

#### Agendamento / Notificacoes
- [ ] Scheduler (tarefas em horarios)
- [ ] Tarefas recorrentes
- [ ] Tarefas com delay
- [ ] Notificacoes Windows (toast)
- [ ] Notificacoes por voz
- [ ] Notificacoes email
- [ ] Notificacoes Telegram/Discord

#### Memoria
- [ ] Preferencias
- [ ] Contexto de projetos
- [ ] Historico de tarefas
- [ ] Memoria episodica
- [ ] Busca semantica
- [ ] Esquecer/apagar

#### Memoria de ferramentas
- [ ] Router inteligente
- [ ] Nao repetir erro
- [ ] Preferir solucao que funcionou
- [ ] Historico de sessoes
- [ ] Sumarizacao periodica

#### Seguranca
- [ ] Cofre de senhas
- [ ] 2FA para acoes criticas
- [ ] Log de tudo
- [ ] Reverter acao destrutiva
- [ ] Sandbox para codigo
- [ ] Limites de gasto

#### Testes / Qualidade
- [ ] Testes automatizados
- [ ] CI/CD
- [ ] Health check
- [ ] Metricas de uso
- [ ] Teste de carga

---

<a id="pt-longo-prazo"></a>

### Longo prazo

#### FASE 40 - UI propria (bloqueada)
![Bloqueada](https://img.shields.io/badge/-BLOQUEADA-red?style=flat-square)

**Bloqueada por:** FASE 27 + FASE 30 + FASE 31

- [ ] Design (Figma)
- [ ] Frontend do zero
- [ ] WebSocket
- [ ] Sidebar de conversas
- [ ] Painel de tasks
- [ ] Overlay visual integrado
- [ ] Botoes de acao rapida
- [ ] Migracao do Open WebUI

#### Meta / Estrategico
- [ ] MYRA rodando 24/7 em background
- [ ] MYRA acorda sozinha e faz tarefas agendadas
- [ ] MYRA aprende preferencias
- [ ] MYRA proativa
- [ ] Multi-usuario (perfis)
- [ ] Auto-diagnostico
- [ ] Auto-recovery
- [ ] Multi-agent (Researcher, Coder, etc.)

---

<a id="pt-canceladas"></a>

### Canceladas

#### FASE 9 - Customizacao profunda do Open WebUI
![Cancelada](https://img.shields.io/badge/-CANCELADA-red?style=flat-square)

**Decisao (04/10/2026):** manter Open WebUI oficial + customizacoes minimas.

- ~~9.5 - Remover "(Open WebUI)" do titulo~~
- ~~9.6 - Trocar textos internos~~
- ~~9.7 - Logo e favicon custom~~
- ~~9.8 - CSS custom~~
- ~~9.9 - JS custom~~
- ~~9.10 - System prompt global~~
- ~~9.11 - Splash screen custom~~
- ~~9.12 - Modelo "MYRA" como padrao~~
- ~~9.13 - Fork do Open WebUI~~

---

<a id="pt-resumo"></a>

### Resumo por area

| Area | Itens | Status |
|------|-------|--------|
| Autonomia (FASE 22.x + 24.x) | 18 | ![80%](https://img.shields.io/badge/-80%25-brightgreen?style=flat-square) |
| Visao com coordenadas (FASE 25) | 6 | ![0%](https://img.shields.io/badge/-0%25-yellow?style=flat-square) |
| Ciclo autonomo (FASE 26) | 5 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| Overlay TARS (FASE 27) | 7 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| Mobile (FASE 28) | 17 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| CarPlay (FASE 29) | 6 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| Distribuicao (FASE 30) | 6 | ![5%](https://img.shields.io/badge/-5%25-lightgrey?style=flat-square) |
| Interface propria (FASE 31 + 40) | 18 | ![0%](https://img.shields.io/badge/-0%25-red?style=flat-square) |
| Voz / Audio (FASE 14) | 5 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| YouTube (FASE 20) | 12 | ![70%](https://img.shields.io/badge/-70%25-green?style=flat-square) |
| Geracao de midia (FASE 12) | 6 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| Arquivos (FASE 15) | 12 | ![60%](https://img.shields.io/badge/-60%25-yellow?style=flat-square) |
| Web | 14 | ![50%](https://img.shields.io/badge/-50%25-yellow?style=flat-square) |
| Computer Use | 15 | ![70%](https://img.shields.io/badge/-70%25-yellow?style=flat-square) |
| Vision | 12 | ![40%](https://img.shields.io/badge/-40%25-yellow?style=flat-square) |
| Coding Agent | 10 | ![60%](https://img.shields.io/badge/-60%25-yellow?style=flat-square) |
| Email | 12 | ![50%](https://img.shields.io/badge/-50%25-yellow?style=flat-square) |
| Info do mundo | 8 | ![20%](https://img.shields.io/badge/-20%25-lightgrey?style=flat-square) |
| Analise de dados | 6 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| Windows / Sistema | 8 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| Terminal | 10 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| Agendamento | 7 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| Memoria | 12 | ![15%](https://img.shields.io/badge/-15%25-lightgrey?style=flat-square) |
| Seguranca | 6 | ![45%](https://img.shields.io/badge/-45%25-yellow?style=flat-square) |
| Dispositivos | 4 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| Testes | 6 | ![5%](https://img.shields.io/badge/-5%25-lightgrey?style=flat-square) |
| Documentacao | 6 | ![60%](https://img.shields.io/badge/-60%25-yellow?style=flat-square) |
| Meta / Estrategico | 8 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |

**Total: ~244 itens**
**Progresso geral: ~67%**

---

## Proxima acao

**FASE 25 - Visao com Coordenadas** (`vision_locate`)

1. Investigar como `/see` fala com llm-eyes
2. Provar conceito com prompt de coordenadas
3. Implementar `/vision_locate(descricao)`
4. Normalizar coordenadas (DPI, resolucao)
5. Integrar no planner
6. Testar end-to-end

**Meta:** MYRA consegue "ver" um botao pela descricao e clicar nele.

---

<a id="english"></a>

## English (EN)

### Legend

| Badge | Meaning |
|-------|---------|
| ![Done](https://img.shields.io/badge/-DONE-brightgreen?style=flat-square) | Phase 100% complete |
| ![In Progress](https://img.shields.io/badge/-IN_PROGRESS-yellow?style=flat-square) | Currently being worked on |
| ![Pending](https://img.shields.io/badge/-PENDING-lightgrey?style=flat-square) | Planned, not started |
| ![Blocked](https://img.shields.io/badge/-BLOCKED-red?style=flat-square) | Depends on another phase |
| ![Cancelled](https://img.shields.io/badge/-CANCELLED-red?style=flat-square) | Discarded |

### Contents

- [Completed phases](#en-completed)
- [Next phases](#en-next)
- [Mid-term](#en-mid)
- [Long-term](#en-long)
- [Cancelled](#en-cancelled)
- [Summary by area](#en-summary)

---

<a id="en-completed"></a>

### Completed phases

#### Base (PHASES 0-10, 15-19)
![Done](https://img.shields.io/badge/-DONE-brightgreen?style=flat-square)

- [x] FastAPI server (agent.py) with ~90 routes
- [x] Browser (Playwright): 10 routes
- [x] Vision (see_image via llama-server)
- [x] Email (IMAP/SMTP Gmail): 10 routes
- [x] Utilities: time, notes, weather, run_python
- [x] Files (workspace): 7 routes
- [x] Web search (DuckDuckGo)
- [x] PC automation (PHASE 16): 12 routes
- [x] Chats (PHASE 10): 5 routes
- [x] CodeAgent (PHASE 17): 21 tools
- [x] Destructive-action confirmation system

#### YouTube (PHASE 20)
![Done](https://img.shields.io/badge/-DONE-brightgreen?style=flat-square)

- [x] 6 routes: transcript, summarize, ask, save, list, read
- [x] PHASE 20.1 - Automatic language detection
- [x] VTT encoding fix

#### Autonomous agent (PHASE 22-light)
![Done](https://img.shields.io/badge/-DONE-brightgreen?style=flat-square)

- [x] tasks/simple_task.py - planner + loop + retry
- [x] Route /task_simple
- [x] Open WebUI integration (task_run)
- [x] Multilingual bug fix

#### Real autonomy (PHASE 24.1-24.3)
![Done](https://img.shields.io/badge/-DONE-brightgreen?style=flat-square)

- [x] **24.1** - Adaptive loop (LLM decides one step at a time)
- [x] **24.2** - Structured tools (6)
- [x] **24.3** - Real cancellation via shared flag

#### Bridge + Widget (PHASE 24.4)
![Done](https://img.shields.io/badge/-DONE-brightgreen?style=flat-square)

- [x] Chrome MV3 extension with 12 tools
- [x] Serialized polling (recursive setTimeout)
- [x] Tauri widget with pill/square mode
- [x] Speech bubble, animated mouth, eyes following mouse
- [x] Lock position + always on top (separate)
- [x] Settings: theme, compact, sound, DND

#### Infrastructure
![Done](https://img.shields.io/badge/-DONE-brightgreen?style=flat-square)

- [x] Ollama with CUDA v12
- [x] Open WebUI in Docker
- [x] nginx proxy with sub_filter
- [x] Scripts abrir_tudo.ps1
- [x] Chrome with dedicated profile
- [x] OPENWEBUI_API_KEY in env var

#### Documentation
![Done](https://img.shields.io/badge/-DONE-brightgreen?style=flat-square)

- [x] Professional README.md with badges
- [x] HANDOFF.md
- [x] ROADMAP.md (this file)
- [x] Robust .gitignore

---

<a id="en-next"></a>

### Next phases

#### PHASE 25 - Vision with Coordinates
![In Progress](https://img.shields.io/badge/-IN_PROGRESS-yellow?style=flat-square)

**Goal:** vision_locate(description) returns X/Y coordinates

- [ ] /vision_locate(description) - returns dict with x, y, confidence
- [ ] /vision_click(description) - locates + clicks
- [ ] /vision_type(field_desc, text) - locates + types
- [ ] Coordinate normalization (DPI, resolution)
- [ ] Fallback: OCR via Tesseract
- [ ] Planner integration

**Free tools:** llm-eyes (already running), Tesseract, OmniParser, UI-TARS

#### PHASE 26 - Complete Autonomous Loop
![Pending](https://img.shields.io/badge/-PENDING-lightgrey?style=flat-square)

**Goal:** LLM acts, observes, verifies, recovers

- [ ] _observe() - screenshot + analysis after each action
- [ ] _verify(goal) - check if achieved
- [ ] _recover(error) - new strategy
- [ ] Task persistence (resume after crash)
- [ ] Pause/resume without losing context

#### PHASE 27 - TARS Visual Overlay
![Pending](https://img.shields.io/badge/-PENDING-lightgrey?style=flat-square)

**Goal:** see animated cursor, highlight, active border

- [ ] Transparent click-through Tauri window
- [ ] Event channel (SSE /task_events already exists)
- [ ] Animated cursor
- [ ] Target highlight before click
- [ ] Visual states (observing/thinking/executing)
- [ ] Visible mouse trajectory
- [ ] Visual cancellation

#### PHASE 28 - Mobile Control
![Pending](https://img.shields.io/badge/-PENDING-lightgrey?style=flat-square)

##### 28.1 - Remote access infrastructure (Tailscale)
- [ ] Tailscale on Windows PC
- [ ] Tailscale on iPhone
- [ ] Stable IP (100.x.y.z)

##### 28.2 - Telegram Bot
- [ ] Bot in @BotFather
- [ ] Webhook in agent.py
- [ ] Commands: /task, /status, /cancel, /screenshot, /see
- [ ] Auto-notification on completion
- [ ] chat_id authentication

##### 28.3 - Native iOS App
- [ ] App shell (Swift/SwiftUI)
- [ ] Chat screen
- [ ] Lock screen widget
- [ ] Home screen widget
- [ ] Siri Shortcuts
- [ ] APNs notifications

#### PHASE 29 - CarPlay Integration
![Pending](https://img.shields.io/badge/-PENDING-lightgrey?style=flat-square)

**Path:** Audio App (appears as player in CarPlay)

- [ ] iOS shell base + Tailscale
- [ ] TTS (Piper) + STT (Whisper)
- [ ] CarPlay Audio App framework
- [ ] MPNowPlayingInfoCenter
- [ ] Steering wheel buttons mapped
- [ ] Publishing (optional: TestFlight)

#### PHASE 30 - Distribution
![Pending](https://img.shields.io/badge/-PENDING-lightgrey?style=flat-square)

- [ ] cargo tauri build + .exe
- [ ] NSIS installer
- [ ] Auto-start on boot
- [ ] System tray
- [ ] Native Windows notification
- [ ] Connection indicator in widget

#### PHASE 31 - Custom Interface
![Blocked](https://img.shields.io/badge/-BLOCKED-red?style=flat-square)

**Blocked by:** PHASE 27 (overlay) + PHASE 30 (distribution)

- [ ] Design (Figma)
- [ ] Svelte/SolidJS frontend
- [ ] WebSocket with agent.py
- [ ] Chat with markdown
- [ ] Running tasks panel
- [ ] Open WebUI migration

---

<a id="en-mid"></a>

### Mid-term

#### PHASE 22.5+ - Agent polish
- [ ] Improve respond (direct answers)
- [ ] More tools in task_run
- [ ] Structured logs
- [ ] "I'll ask before acting" mode

#### PHASE 24.5 - SQLite persistence
- [ ] Tasks survive restart
- [ ] Queryable history
- [ ] SQLite schema

#### PHASE 14 - Voice and Audio
- [ ] TTS + Whisper
- [ ] Wake word ("MYRA, ...")
- [ ] Continuous voice conversation
- [ ] Voice selection

#### PHASE 20.5-20.11 - Advanced YouTube
- [ ] Whisper for videos without captions
- [ ] Vimeo, other sites
- [ ] Extract MP3
- [ ] Download video
- [ ] Playlists
- [ ] Transcript cache
- [ ] Vision on frames

#### PHASE 12 - Media generation
- [ ] Image generation (free API)
- [ ] Editing (crop, resize, filter)
- [ ] Background removal
- [ ] Upscale
- [ ] OCR

#### PHASE 15 - Advanced files
- [ ] Read PDFs
- [ ] Read Excel/CSV
- [ ] Read Word/DOCX
- [ ] Read PowerPoint
- [ ] Convert formats
- [ ] Access outside workspace
- [ ] Compress/decompress
- [ ] Hash, diff
- [ ] Watch folders

#### Advanced web
- [ ] Download files via browser
- [ ] Multi-step forms
- [ ] Auto-login
- [ ] Element screenshot
- [ ] Extract tables
- [ ] Detect CAPTCHA
- [ ] iFrames and shadow DOM
- [ ] Cookies and localStorage
- [ ] Block ads/trackers

#### Advanced Computer Use
- [ ] Drag and drop
- [ ] Clipboard
- [ ] Maximize/minimize windows
- [ ] Open/close apps
- [ ] Processes
- [ ] Unexpected popups
- [ ] Multiple monitors

#### Advanced Vision
- [ ] Larger model (Qwen2.5-VL-7B)
- [ ] Identify buttons
- [ ] Element coordinates (covered by PHASE 25)
- [ ] Compare before/after
- [ ] Detect visual errors
- [ ] Embedded OCR
- [ ] CAPTCHA detection

#### Advanced Coding Agent
- [ ] Auto-fix bugs
- [ ] Run entire project
- [ ] Git via tool
- [ ] Create complete project
- [ ] Analyze project
- [ ] Install dependencies
- [ ] Run tests + interpret
- [ ] Loop: run -> see error -> fix -> run

#### Advanced Email
- [ ] Download attachments
- [ ] Analyze attachments
- [ ] Forward
- [ ] Create draft
- [ ] Archive
- [ ] Detect deadlines
- [ ] Summarize thread

#### World info
- [ ] News (RSS)
- [ ] Prices (stocks, crypto)
- [ ] Maps / routes
- [ ] Translation
- [ ] Currency rates
- [ ] Google Calendar
- [ ] Google Contacts
- [ ] RAG on local PDFs

#### Windows / System
- [ ] Install software (winget)
- [ ] Update software
- [ ] Configure apps
- [ ] Diagnosis
- [ ] Monitor resources
- [ ] Auto backup

#### Terminal
- [ ] Interpret output
- [ ] Structured PowerShell
- [ ] Structured CMD
- [ ] npm/yarn/pnpm
- [ ] pip/poetry/uv
- [ ] Docker
- [ ] Ollama
- [ ] Git
- [ ] Adaptive timeout
- [ ] Background + polling

#### Scheduling / Notifications
- [ ] Scheduler (tasks at times)
- [ ] Recurring tasks
- [ ] Delayed tasks
- [ ] Windows notifications (toast)
- [ ] Voice notifications
- [ ] Email notifications
- [ ] Telegram/Discord notifications

#### Memory
- [ ] Preferences
- [ ] Project context
- [ ] Task history
- [ ] Episodic memory
- [ ] Semantic search
- [ ] Forget/delete

#### Tool memory
- [ ] Smart router
- [ ] Don't repeat errors
- [ ] Prefer solutions that worked
- [ ] Session history
- [ ] Periodic summarization

#### Security
- [ ] Password vault
- [ ] 2FA for critical actions
- [ ] Full audit log
- [ ] Revert destructive action
- [ ] Sandbox for code execution
- [ ] Spending limits

#### Testing / Quality
- [ ] Automated tests
- [ ] CI/CD
- [ ] Health check
- [ ] Usage metrics
- [ ] Load testing

---

<a id="en-long"></a>

### Long-term

#### PHASE 40 - Custom UI (blocked)
![Blocked](https://img.shields.io/badge/-BLOCKED-red?style=flat-square)

**Blocked by:** PHASE 27 + PHASE 30 + PHASE 31

- [ ] Design (Figma)
- [ ] Frontend from scratch
- [ ] WebSocket
- [ ] Conversation sidebar
- [ ] Tasks panel
- [ ] Integrated visual overlay
- [ ] Quick action buttons
- [ ] Open WebUI migration

#### Strategic / Meta
- [ ] MYRA running 24/7 in background
- [ ] MYRA wakes up alone and does scheduled tasks
- [ ] MYRA learns preferences
- [ ] Proactive MYRA
- [ ] Multi-user (profiles)
- [ ] Self-diagnosis
- [ ] Self-recovery
- [ ] Multi-agent (Researcher, Coder, etc.)

---

<a id="en-cancelled"></a>

### Cancelled

#### PHASE 9 - Deep Open WebUI customization
![Cancelled](https://img.shields.io/badge/-CANCELLED-red?style=flat-square)

**Decision (2026-10-04):** keep official Open WebUI + minimal customizations.

- ~~9.5 - Remove "(Open WebUI)" from title~~
- ~~9.6 - Change internal texts~~
- ~~9.7 - Custom logo and favicon~~
- ~~9.8 - Custom CSS~~
- ~~9.9 - Custom JS~~
- ~~9.10 - Global system prompt~~
- ~~9.11 - Custom splash screen~~
- ~~9.12 - "MYRA" as default model~~
- ~~9.13 - Open WebUI fork~~

---

<a id="en-summary"></a>

### Summary by area

| Area | Items | Status |
|------|-------|--------|
| Autonomy (PHASE 22.x + 24.x) | 18 | ![80%](https://img.shields.io/badge/-80%25-brightgreen?style=flat-square) |
| Vision with coordinates (PHASE 25) | 6 | ![0%](https://img.shields.io/badge/-0%25-yellow?style=flat-square) |
| Autonomous loop (PHASE 26) | 5 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| TARS overlay (PHASE 27) | 7 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| Mobile (PHASE 28) | 17 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| CarPlay (PHASE 29) | 6 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| Distribution (PHASE 30) | 6 | ![5%](https://img.shields.io/badge/-5%25-lightgrey?style=flat-square) |
| Custom interface (PHASE 31 + 40) | 18 | ![0%](https://img.shields.io/badge/-0%25-red?style=flat-square) |
| Voice / Audio (PHASE 14) | 5 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| YouTube (PHASE 20) | 12 | ![70%](https://img.shields.io/badge/-70%25-green?style=flat-square) |
| Media generation (PHASE 12) | 6 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| Files (PHASE 15) | 12 | ![60%](https://img.shields.io/badge/-60%25-yellow?style=flat-square) |
| Web | 14 | ![50%](https://img.shields.io/badge/-50%25-yellow?style=flat-square) |
| Computer Use | 15 | ![70%](https://img.shields.io/badge/-70%25-yellow?style=flat-square) |
| Vision | 12 | ![40%](https://img.shields.io/badge/-40%25-yellow?style=flat-square) |
| Coding Agent | 10 | ![60%](https://img.shields.io/badge/-60%25-yellow?style=flat-square) |
| Email | 12 | ![50%](https://img.shields.io/badge/-50%25-yellow?style=flat-square) |
| World info | 8 | ![20%](https://img.shields.io/badge/-20%25-lightgrey?style=flat-square) |
| Data analysis | 6 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| Windows / System | 8 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| Terminal | 10 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| Scheduling | 7 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| Memory | 12 | ![15%](https://img.shields.io/badge/-15%25-lightgrey?style=flat-square) |
| Security | 6 | ![45%](https://img.shields.io/badge/-45%25-yellow?style=flat-square) |
| Devices | 4 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |
| Testing | 6 | ![5%](https://img.shields.io/badge/-5%25-lightgrey?style=flat-square) |
| Documentation | 6 | ![60%](https://img.shields.io/badge/-60%25-yellow?style=flat-square) |
| Strategic / Meta | 8 | ![0%](https://img.shields.io/badge/-0%25-lightgrey?style=flat-square) |

**Total: ~244 items**
**Overall progress: ~67%**

---

## Next action

**PHASE 25 - Vision with Coordinates** (vision_locate)

1. Investigate how /see talks to llm-eyes
2. Prove concept with coordinate prompt
3. Implement /vision_locate(description)
4. Normalize coordinates (DPI, resolution)
5. Integrate into planner
6. Test end-to-end

**Goal:** MYRA can "see" a button by description and click it.

---

**Last updated:** 2026-10-12
