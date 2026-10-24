# MYRA - Roadmap

[![Progress](https://img.shields.io/badge/Progress-32%25-orange?style=flat-square)]()
[![Active Phase](https://img.shields.io/badge/Active_Phase-26-blue?style=flat-square)]()
[![Phases](https://img.shields.io/badge/Phases-31-purple?style=flat-square)]()
[![Updated](https://img.shields.io/badge/Updated-2026-10-22-lightgrey?style=flat-square)]()
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

#### FASE 25 - Visao com Coordenadas
![Concluida](https://img.shields.io/badge/-CONCLUIDA-brightgreen?style=flat-square)

**Meta:** vision_locate(descricao) retorna coordenadas X/Y

- [x] `/vision_locate(descricao)` - retorna dict com x, y, confidence
- [x] `/vision_click(descricao)` - localiza + clica
- [x] `/vision_type(campo_desc, texto)` - localiza + digita
- [x] Normalizacao de coordenadas (DPI, resolucao)
- [x] Fallback: OCR via Tesseract
- [x] Integracao no planner

**Ferramentas free:** llm-eyes (ja tem), Tesseract, OmniParser, UI-TARS

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

#### FASE 26 - Ciclo Autonomo Completo
![Em progresso](https://img.shields.io/badge/-EM_PROGRESSO-yellow?style=flat-square)

**Meta:** LLM age, observa, verifica, corrige

- [x] _observar() - avalia cada acao com resultado + LLM; screenshot enviado ao modelo visual local, com fallback textual (`computer/observer.py`).
- [x] _verificar(objetivo) - `tasks/autonomy.py::verificar`: so declara sucesso com evidencia do observer (acao ok + objetivo atingido); nunca declara sucesso sem evidencia.
- [x] _recuperar(erro) - `tasks/autonomy.py::recuperar`: nova estrategia sugerida por ferramenta, acoes bloqueadas por assinatura e limites explicitos (`MAX_TENTATIVAS_POR_ACAO`, `LIMITE_RECUPERACOES`).
- [x] Task persistence (retomar apos crash) - `tasks/task_store.py` (SQLite, `%LOCALAPPDATA%\MYRA\myra_tasks.sqlite3`) grava objetivo, passo, historico, estado e eventos; tasks de um processo morto viram `interrompido` no startup e sao retomadas por `/task_resume`.
- [x] Pausa/continua sem perder contexto - `POST /task_pause` interrompe no proximo ponto seguro e persiste o estado; `POST /task_resume` continua do passo seguinte com historico, observacoes, verificacoes e recuperacoes preservados.
- [x] Rotas de apoio: `GET /task_pendentes`, `GET /task_detalhe/{task_id}` (historico + eventos de auditoria).
- [x] Testes do ciclo: `tests/` com 43 testes (`python -m unittest discover -s tests -t .`) cobrindo verificacao, recuperacao, pausa/retomada, retomada apos crash, erros e rotas HTTP.
- [x] Validacao end-to-end com Ollama real (`qwen2.5:7b`): criacao de arquivo concluida por evidencia do observer, falha com motivo explicito e pausa/retomada com contexto preservado (executada em 2026-10-15).
- [x] Observacao com screenshot dedicado no observer, fallback textual se captura/modelo visual falhar.
- [x] Corrigir Unicode/encoding no `computer/vision_locate.py` standalone: a saida de stdout/stderr usa `backslashreplace` para caracteres fora da code page ativa.
- [x] Corrigir falso sucesso de `vision_locate`/`vision_click`/`vision_type`: alvo ausente, resposta incompleta ou coordenadas ausentes retornam `status: erro` e nao executam clique/digitacao.
- [x] Validar limites das coordenadas visuais antes de acionar o mouse, inclusive respostas antigas sem metadados de resolucao.
- [x] Rejeitar tipos invalidos em descricao e caminho do screenshot com erros estruturados, sem excecoes de tipo escaparem para o executor.
- [x] Verificacao deterministica de objetivos web: navegar nao satisfaz pedido de leitura, ler nao satisfaz pedido de clique, e extracao exige texto do corpo da pagina.
- [x] Validacao de `GET /task_pendentes`: rejeita limites negativos com HTTP 422 e normaliza inteiros acima de int64 sem perder tasks.

#### FASE 27 - Overlay Visual TARS
![Concluida](https://img.shields.io/badge/-CONCLUIDA-brightgreen?style=flat-square)

**Meta:** ver o cursor animado, highlight, borda ativa

- [x] Janela Tauri transparente fullscreen, inicialmente oculta e nativamente click-through
- [x] Canal SSE conectado a `/task_events`
- [x] Cursor visual animado nos alvos publicados pelo sistema de visao
- [x] Highlight do alvo antes de `vision_click` / `vision_type`
- [x] Estados visuais (observando/pensando/executando/concluido/erro)
- [x] Trajetoria visual entre alvos sucessivos publicados
- [x] Cancelamento refletido visualmente quando o estado da task muda

#### FASE 27.5 - Integracao REA
![Em progresso](https://img.shields.io/badge/-EM_PROGRESSO-yellow?style=flat-square)

**Repo:** https://github.com/morluto/rea
**Descricao:** ferramenta opcional de analise local de apps JavaScript/Electron.
**Licenca:** MIT | **Requer:** Node.js 22.19+, 24.11+ ou 26+.

- [x] Criado tasks/rea_tools.py com rea_status, rea_catalog e rea_analyze_javascript.
- [x] Ferramentas registradas no planner e regras para uso autorizado.
- [x] Analise limitada a raizes configuradas; sem instalacao global nem execucao no startup.
- [x] Validado em 2026-10-22 com MYRA_REA_ALLOWED_ROOTS apontando para C:\\computer-agent e analise REA bem-sucedida de widget-tauri\\ui (evidencia JSON; resultado truncado pelo limite de saida de 12.000 caracteres). A variavel foi configurada para a execucao de validacao; configuracao persistente ainda depende do ambiente de deploy.
- [x] Conexao MCP real via SDK oficial e descoberta de 207 ferramentas com esquemas JSON.
- [x] Ponte MCP integrada: rea_mcp_list_tools e rea_mcp_call, com allowlist explicita de 11 ferramentas de leitura, validacao de raiz autorizada para analise JavaScript e limites de tamanho/timeout.
- [x] Validada chamada MCP real de `analyze_javascript_application` no `workspace\\rea_smoke_test`: retornou Evidence com `status=ok`, sem truncamento, respeitando a raiz autorizada.
- [ ] Validar as ferramentas que dependem de um provedor binario aberto; `current_document` respondeu `target_unavailable` enquanto nenhum app estava aberto.

**Aviso legal:** usar somente software proprio ou explicitamente autorizado. Detalhes em PHASE27_5_REA.md.

### FASE 28 - Controle Mobile
![Em progresso](https://img.shields.io/badge/-EM_PROGRESSO-yellow?style=flat-square)

##### 28.1 - Infra de acesso remoto (Tailscale)
- [x] Diagnostico local implementado em tasks/remote_access.py e GET /remote_access/status.
- [x] O diagnostico valida o IPv4 Tailscale do proprio PC e nao expoe a lista de peers.
- [x] Documentadas instalacao oficial e etapas de conexao: PHASE28_1_TAILSCALE.md.
- [ ] Instalar e autenticar Tailscale no PC Windows.
- [ ] Instalar e autenticar Tailscale no iPhone na mesma conta.
- [ ] Antes de acesso direto remoto, implementar autenticacao de API e restringir rotas sensiveis.

##### 28.2 - Telegram Bot
- [ ] Criar bot no @BotFather e configurar token/chat IDs no Windows.
- [x] Integracao via long polling em tasks/telegram_bot.py (sem porta publica/webhook).
- [x] Comandos implementados: /task, /status, /cancel, /pause, /resume, /screenshot, /see, /help.
- [x] Autenticacao por allowlist MYRA_TELEGRAM_ALLOWED_CHAT_IDS; bot desativado sem token/allowlist.
- [x] Rotas locais /telegram/status, /telegram/start, /telegram/stop.
- [ ] Validar todos os comandos com Telegram real e configurar notificacoes no dispositivo.

##### 28.3 - App iOS Nativo
- [x] API remota separada e protegida por MYRA_REMOTE_API_TOKEN (Bearer); desativada sem segredo.
- [x] Endpoints autenticados: GET /remote/v1/status, POST /remote/v1/task, POST /remote/v1/cancel.
- [x] Scaffold SwiftUI inicial em mobile-ios/MyraMobile (status, tarefa, cancelamento).
- [x] Token guardado no Keychain; HTTPS obrigatorio fora de localhost.
- [ ] Criar projeto Xcode e compilar/testar no macOS (nao disponivel neste PC Windows).
- [ ] Configurar e validar Tailscale Serve com caminho restrito /remote/v1.
- [ ] Widgets Lock Screen/Home Screen, Siri Shortcuts e notificacoes APNs.

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
![Concluida pela FASE 26](https://img.shields.io/badge/-CONCLUIDA-brightgreen?style=flat-square)

- [x] Tasks sobrevivem a restart - `tasks/task_store.py` + `/task_resume` (tasks de um processo morto ficam `interrompido` no startup)
- [x] Historico consultavel - `GET /task_detalhe/{task_id}` (historico + eventos) e `GET /task_pendentes`
- [x] Schema SQLite - tabelas `tasks` e `task_eventos` em `%LOCALAPPDATA%\MYRA\myra_tasks.sqlite3`

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
| Visao com coordenadas (FASE 25) | 6 | ![100%](https://img.shields.io/badge/-100%25-brightgreen?style=flat-square) |
| Ciclo autonomo (FASE 26) | 5 | ![80%](https://img.shields.io/badge/-80%25-yellow?style=flat-square) |
| Overlay TARS (FASE 27) | 7 | ![100%](https://img.shields.io/badge/-100%25-brightgreen?style=flat-square) |
| Mobile (FASE 28) | 19 | ![58%](https://img.shields.io/badge/-58%25-yellow?style=flat-square) |
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

**Checklist PT-BR: 242 itens rastreados**
**Progresso do checklist PT-BR: 33% (79 de 242 itens marcados).**

*Este percentual é a contagem simples dos checkboxes da seção em português; não pondera complexidade nem significa prontidão para produção.*

---

## Proxima acao

**Ordem revisada em 2026-10-22**, apos corrigir os dois bloqueadores da visao:

1. **Concluir a validacao real da FASE 26 no navegador**: uma task real de dois passos abriu `https://example.com`, leu o corpo via `browser_read_active_tab` e extraiu o titulo `Example Domain` e o primeiro paragrafo. O verificador bloqueou o sucesso prematuro apos a navegacao. Ainda falta validar recuperacao e pausa/retomada reais.
2. **FASE 27.5 (REA):** analise real do app autorizado `widget-tauri\\ui` passou em 2026-10-22 com raiz autorizada configurada para a execucao; verificar configuracao persistente no ambiente final.
3. **Fechar FASE 28 (controle mobile)**: testar comandos no Telegram real, configurar Tailscale e validar a API remota protegida.
4. **FASE 30 (distribuicao)**: gerar e testar o instalador Windows; depois priorizar voz/interface propria conforme o objetivo do produto.

**Ultima validacao automatizada (2026-10-22):** `pytest -q` — 1.017 passed, 9 skipped, 52 xfailed, 79 warnings e 2.907 subtests aprovados (115,58s). Os `xfail` sao falhas esperadas/documentadas e ainda merecem triagem.

**Validacao real parcial (2026-10-22):** 9 testes opt-in de integracao passaram com Ollama, servico de visao, backend e Browser Bridge ativos. Uma task real de dois passos abriu `https://example.com`, leu o corpo via `browser_read_active_tab` e extraiu o titulo `Example Domain` e o primeiro paragrafo. O verificador deterministico impediu sucesso prematuro apos a navegacao. Recuperacao real e pausa/retomada no navegador continuam pendentes.

**Nota:** a FASE 25 (`vision_locate`) esta concluida e a FASE 24.5 foi concluida pela FASE 26.

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

#### PHASE 25 - Vision with Coordinates
![Done](https://img.shields.io/badge/-DONE-brightgreen?style=flat-square)

**Goal:** vision_locate(description) returns X/Y coordinates

- [x] /vision_locate(description) - returns dict with x, y, confidence
- [x] /vision_click(description) - locates + clicks
- [x] /vision_type(field_desc, text) - locates + types
- [x] Coordinate normalization (DPI, resolution)
- [x] Fallback: OCR via Tesseract
- [x] Planner integration

**Free tools:** llm-eyes (already running), Tesseract, OmniParser, UI-TARS

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

#### PHASE 26 - Complete Autonomous Loop
![In progress](https://img.shields.io/badge/-IN_PROGRESS-yellow?style=flat-square)

**Goal:** LLM acts, observes, verifies, recovers

- [x] _observe() - evaluates each action with tool result + LLM; screenshot is sent to the local vision model, with text fallback (`computer/observer.py`).
- [x] _verify(goal) - `tasks/autonomy.py::verificar`: success is only declared with observer evidence (action ok + goal achieved); never claims success without evidence.
- [x] _recover(error) - `tasks/autonomy.py::recuperar`: per-tool alternative strategy, blocked action signatures and explicit limits (`MAX_TENTATIVAS_POR_ACAO`, `LIMITE_RECUPERACOES`).
- [x] Task persistence (resume after crash) - `tasks/task_store.py` (SQLite) stores goal, step, history, state and events; tasks from a dead process become `interrompido` at startup and are resumed by `/task_resume`.
- [x] Pause/resume without losing context - `POST /task_pause` stops at the next safe point and persists state; `POST /task_resume` continues from the next step with history, observations, verifications and recoveries preserved.
- [x] Support routes: `GET /task_pendentes`, `GET /task_detalhe/{task_id}` (history + audit events).
- [x] Loop tests: `tests/` with 43 tests (`python -m unittest discover -s tests -t .`).
- [x] End-to-end validation with real Ollama (`qwen2.5:7b`): file creation concluded by observer evidence, failure with explicit reason, and pause/resume with preserved context (run on 2026-10-15).
- [x] Dedicated screenshot observation in the observer, with text fallback if capture/vision inference fails.
- [x] Standalone Unicode-safe console output in `computer/vision_locate.py`; unencodable OCR characters are escaped rather than crashing on legacy Windows code pages.
- [x] Vision tools return explicit errors when no target is found or coordinates are missing; click/type do not execute without a validated target.
- [x] Validate visual coordinate bounds before mouse actions, including legacy results without resolution metadata.
- [x] Reject invalid description and screenshot-path types with structured errors rather than leaking type exceptions to the executor.

#### PHASE 27 - TARS Visual Overlay
![Completed](https://img.shields.io/badge/-COMPLETED-brightgreen?style=flat-square)

**Goal:** see animated cursor, highlight, active border

- [x] Transparent fullscreen Tauri window, initially hidden and natively click-through
- [x] SSE channel connected to `/task_events`
- [x] Animated visual cursor at targets published by vision tools
- [x] Target highlight before `vision_click` / `vision_type`
- [x] Visual states (observing/thinking/executing/done/error)
- [x] Visible trajectory between successive published targets
- [x] Cancellation reflected visually when task state changes

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
![Completed by PHASE 26](https://img.shields.io/badge/-COMPLETED-brightgreen?style=flat-square)

- [x] Tasks survive restart - `tasks/task_store.py` + `/task_resume`
- [x] Queryable history - `GET /task_detalhe/{task_id}` and `GET /task_pendentes`
- [x] SQLite schema - `tasks` and `task_eventos` tables

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
| Vision with coordinates (PHASE 25) | 6 | ![100%](https://img.shields.io/badge/-100%25-brightgreen?style=flat-square) |
| Autonomous loop (PHASE 26) | 5 | ![80%](https://img.shields.io/badge/-80%25-yellow?style=flat-square) |
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

**PT-BR checklist: 242 tracked items**
**PT-BR checklist progress: 33% (79 of 242 items checked).**

*This is a simple count of checkboxes in the Portuguese section; it does not weight complexity or imply production readiness.*

---

## Next action

**Order revised on 2026-10-22:**

1. **Finish PHASE 26 real-browser validation**: a real two-step task opened `https://example.com`, read the body with `browser_read_active_tab`, and extracted `Example Domain` plus the first paragraph. The verifier blocked premature completion after navigation; real recovery and pause/resume remain pending.
2. **PHASE 27.5 (REA):** real analysis of the authorized `widget-tauri\ui` app passed on 2026-10-22 with an allowed root configured for the validation process; confirm persistent configuration in the final environment.
3. **PHASE 28 mobile control**: validate real Telegram commands, Tailscale, and the protected remote API.
4. **PHASE 30 distribution**: build and test the Windows installer before prioritizing the native UI and voice.

**Note:** PHASE 25 (`vision_locate`) is complete and PHASE 24.5 was completed by PHASE 26.

---

**Last updated:** 2026-10-24


## PHASE 32 - Universal Windows Application Access

- [x] 32.1 - Discover app shortcuts from per-user/all-users Start Menu and Desktop.
- [x] 32.2 - Expose app inventory through FastAPI (`POST /pc_list_applications`) and open-app API (`POST /pc_open_application`).
- [x] 32.3 - Register app inventory/open actions as planner tools.
- [x] 32.4 - Open a known shortcut by exact/unique name; reject ambiguous matches.
- [x] 32.5 - Add UI Automation (UIA) control listing with name/type/AutomationId.
- [x] 32.6 - Add controlled UIA actions: click, set text, focus, toggle and select; reject ambiguous/disabled controls.
- [x] 32.7 - Add controlled window actions (minimize/maximize/restore/close) with state verification.
- [ ] 32.8 - Validate multi-application workflows with observe-act-verify and recovery.
  - Progress (2026-10-24): deterministic 2-3 app launch flow now requires `pc_open_application` to return `status=ok` before proceeding to the next app.
  - Added post-launch observation through Windows UI Automation: opening is `ok` only when a matching visible window title is observed; otherwise returns `unverified` and explicitly avoids automatic repeat attempts.
  - Automated tests cover verified visible-window success and unverified launch outcomes. Remaining: validate several real desktop app types, strengthen title matching for localized/dynamic titles, and extend post-action observation to click/type/window workflows.
  - Additional UI Automation guard: `set_text` and `focus` return success only when their resulting value/focus can be read back; generic click/toggle/select responses explicitly state that the downstream effect still needs observation.
  - Safety fix (2026-10-24): `_executar_passo` now immediately stops on `unverified` or `ambiguous` tool results instead of retrying a potentially applied UI action. Regression tests prove that uncertain/ambiguous clicks are executed at most once.
- [x] 32.9 - Expand inventory to installed-app registry entries; only expose a launch target when a concrete existing executable is identified.
  - Safety: never execute registry UninstallString; Start Menu entries remain preferred and duplicate display names are skipped.
  - Validation on 2026-10-24: inventory grew from 333 to 360 entries; 27 registry-only entries were added, 17 with verified executable paths. Entries without safe targets are discoverable but not launchable.

**Security boundary:** no arbitrary command-line execution, no implicit elevation, and no bypass of existing confirmations for consequential actions. Shortcut discovery and launching run as the logged-in Windows user.

---

## FASE FUTURA - Cloud Deployment (24/7)
- [ ] **Objetivo:** Migrar o backend (FastAPI + Telegram Bot) para um VPS (Virtual Private Server).
- [ ] **Motivo:** Permitir que o cérebro do MYRA e o bot do Telegram fiquem online 24/7, independentemente do PC local estar ligado ou desligado.
- [ ] **Arquitetura:** O PC local continuará sendo o 'worker' que executa as ações no navegador (Chrome + Extensão). O VPS receberá os comandos e os enfileirará. Quando o PC ligar, ele puxa a fila e executa.
- [ ] **Status:** Aguardando conclusão das fases locais e validação total do app iOS/API Remota.
