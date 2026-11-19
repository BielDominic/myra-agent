# MYRA - Roadmap

[![Progress](https://img.shields.io/badge/Progress-33%25-orange?style=flat-square)]()
[![Active Phase](https://img.shields.io/badge/Active_Phase-30-blue?style=flat-square)]()
[![Phases](https://img.shields.io/badge/Phases-31-purple?style=flat-square)]()
[![Updated](https://img.shields.io/badge/Updated-2026-10-26-lightgrey?style=flat-square)]()
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

### FASE 32 - MYRA Workspace Nativo, Plugins e Code Studio
![Em progresso](https://img.shields.io/badge/-EM_PROGRESSO-yellow?style=flat-square)

**Objetivo:** trazer para a interface própria as experiências centrais do Open WebUI e criar um ambiente de programação completo.

- [x] Seleção individual e múltipla de conversas com exclusão por conversa e em massa; confirmação própria da interface.
- [x] Respostas com blocos HTML/CSS/JS convertidos em projeto local e preview dentro do chat.
- [x] Importação de imagens no Code Studio e suporte a arrastar/soltar assets para o preview.
- [x] Skills rápidas no composer: Programar, Pesquisar, Design e Revisar.
- [x] Ditado e leitura de respostas usando as APIs de voz disponíveis no WebView.
- [x] Encerrar widget e overlay quando a janela principal é fechada.
- [x] Instalador NSIS com Python 3.14.10, 50 wheels principais offline e Chromium do Playwright incluídos; setup do backend sem downloads do PyPI.
- [x] Primeira biblioteca de referências e fila local de fontes de plugins para avaliação.
- [x] Contrato de arquitetura de plugins documentado em docs/PLUGIN_ARCHITECTURE.md.
- [ ] Runtime seguro de plugins, validação de manifestos, permissões por capacidade, instalação, ativação e rollback.
- [ ] Migrar as ferramentas e skills já existentes do Open WebUI para a interface nativa, preservando BrowserAgent e integrações atuais.
- [ ] Code Studio com editor de linguagem completo, console, logs, testes, árvore de projeto e preview responsivo.
- [ ] Integração de imagens no chat, anexos multimodais e análise visual.
- [ ] STT/TTS locais com Whisper/whisper.cpp e Piper, seleção de modelos e transcrição de áudio.
- [ ] Memória de projeto, sumarização contextual, busca semântica e controles de retenção.
- [x] Reorganizar backups, notas de contexto, relatórios de fase e scripts de patch em pastas dedicadas, preservando os arquivos locais.


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
- [x] Validacao ao vivo do Chrome Browser Bridge (2026-10-24): `get_tabs`, nova aba `example.com`, leitura de DOM/texto e fechamento confirmado; abas preexistentes preservadas.
- [x] Validacao de `GET /task_pendentes`: rejeita limites negativos com HTTP 422 e normaliza inteiros acima de int64 sem perder tasks.
- [x] Revalidacao global em 2026-10-25 apos hardening do Browser Bridge: suite completa pytest passou com 1.148 passed, 9 skipped, 12 xfailed, 3.244 subtests e 1 warning; suite Browser Bridge passou com 92 testes e 171 subtests; teste de token malformado passou com 6 subtests. Commit/push d008332c.

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
![Concluida](https://img.shields.io/badge/-CONCLUIDA-brightgreen?style=flat-square)

**Repo:** https://github.com/morluto/rea
**Descricao:** ferramenta opcional de analise local de apps JavaScript/Electron.
**Licenca:** MIT | **Requer:** Node.js 22.19+, 24.11+ ou 26+.

- [x] Criado tasks/rea_tools.py com rea_status, rea_catalog e rea_analyze_javascript.
- [x] Ferramentas registradas no planner e regras para uso autorizado.
- [x] Analise limitada a raizes configuradas; sem instalacao global nem execucao no startup.
- [x] Validado em 2026-10-22 com MYRA_REA_ALLOWED_ROOTS apontando para C:\\computer-agent e analise REA bem-sucedida de widget-tauri\\ui.
- [x] Configuracao persistente por usuario: raizes autorizadas limitadas a `workspace`, `widget-tauri\ui` e `src-tauri\target\release`; Ghidra 12.1.4 + JDK 21 configurados no ambiente do usuario.
- [x] Conexao MCP real via SDK oficial e descoberta de 207 ferramentas com esquemas JSON.
- [x] Ponte MCP integrada: `rea_mcp_list_tools` e `rea_mcp_call`, allowlist explicita de 15 ferramentas de leitura, validacao de caminhos autorizados, limites de payload/timeout e encaminhamento controlado de variaveis Ghidra ao processo REA.
- [x] Validada chamada MCP real de `analyze_javascript_application` em `widget-tauri\ui`: Evidence com `status=ok`, respeitando a raiz autorizada.
- [x] Ghidra 12.1.4 validado em PE x64 de teste: `inspect_native_instruction`, `address_name` e `resolve_native_call_targets` retornaram Evidence; `inspect_go_binary` e `inspect_rust_binary` passaram no `myra-widget.exe` real.
- [x] Validacao ponta a ponta pela API MYRA (2026-10-25): argumentos diretos do planner normalizados, `inspect_native_instruction` retornou Evidence real (`INT3`, bytes `cc`, 1 byte) no PE x64 de teste; timeout estendido e limitado para operacoes Ghidra demoradas; 18 testes REA passam.
- [x] `PHASE27_5_REA.md` atualizado com resultados e limites verificados. A analise Ghidra completa do `myra-widget.exe` excedeu o prazo do provedor; esse resultado continua explicitamente nao aprovado, embora a analise estatica Go/Rust do mesmo alvo tenha passado.
- [x] Smoke test de provedor concluido: Ghidra suporta inspecao de instrucao/endereco e resolucao de chamadas; `current_document/current_address/current_procedure` sao especificos do Hopper GUI e nao suportados no Windows.

**Aviso legal:** usar somente software proprio ou explicitamente autorizado. Detalhes em PHASE27_5_REA.md.

### FASE 28 - Controle Remoto (Tailscale + Telegram)
![Concluida](https://img.shields.io/badge/-CONCLUIDA-brightgreen?style=flat-square)

##### 28.1 - Infra de acesso remoto (Tailscale)
- [x] Diagnostico local implementado em tasks/remote_access.py e GET /remote_access/status; nao lista peers nem expoe a API.
- [x] Instalacao e passos de conexao documentados em PHASE28_1_TAILSCALE.md.
- [x] Cliente Tailscale 1.104.2 instalado no Windows; estado `Running` e IPv4 Tailscale atribuido.
- [x] Adicionar/autenticar o iPhone no mesmo tailnet. Validado em 2026-10-25: peer `iphone181` (iOS) online em `100.112.204.30`; `tailscale ping` respondeu via DERP(lhr) em ~106-129 ms.
- [x] Tailscale Serve HTTPS configurado para encaminhar exclusivamente `/remote/v1` a `http://127.0.0.1:8000/remote/v1`; validado em 2026-10-25: Bearer correto retorna HTTP 200, sem token retorna HTTP 401 e `/`, `/telegram/status`, `/remote_access/status`, `/openapi.json` e `/docs` retornam HTTP 404. Sem Funnel nem portas publicas.

##### 28.2 - Telegram Bot
- [x] Bot e allowlist configurados no ambiente do Windows sem expor segredos.
- [x] Long polling em tasks/telegram_bot.py; sem webhook, porta publica ou necessidade de expor FastAPI.
- [x] Comandos implementados: /task, /status, /cancel, /pause, /resume, /screenshot, /see, /tasks, /taskinfo, /ping, /models, /model, /newchat e /help.
- [x] Allowlist MYRA_TELEGRAM_ALLOWED_CHAT_IDS; bot desativado sem token/allowlist.
- [x] HTTP 409 interrompe polling local para evitar conflito repetitivo; start() evita threads concorrentes durante encerramento.
- [x] Poll bem-sucedido limpa erro transitorio antigo em `/telegram/status`; teste de regressao cobre recuperacao apos timeout.
- [x] Backend reiniciado apos a correcao; `/telegram/status` confirmou `running=true` e `last_error=null`; `/remote_access/status` confirmou Tailscale `connected` e `api_exposed=false`; a API segue limitada a 127.0.0.1.
- [x] API real do Telegram validada via `getMe`; `getWebhookInfo` confirmou ausencia de webhook (o transporte e long polling).
- [x] Upload real de screenshot para o chat autorizado validado em 2026-10-26; o Telegram aceitou a foto e o helper retornou `photo_uploaded=true`.
- [x] Falha de upload agora e reportada corretamente; a rotina retorna sucesso somente apos o Telegram aceitar `sendPhoto`, com teste de regressao.
- [x] Rotas locais /telegram/status, /telegram/start e /telegram/stop.
- [x] Validacao funcional confirmada pelo usuario (2026-10-26): Telegram funcionou; manter observacao operacional e revalidar se a falha voltar.
- [x] Regressao 2026-10-26: a ausencia de resposta foi associada a HTTP 409 por pollers duplicados. Mutex Windows por hash do token impede uma segunda instancia; apos reiniciar, `/telegram/status` confirmou `running=true` e `last_error=null`; teste real do mutex confirmou primeira instancia aceita e segunda bloqueada.
- [x] Ajuste de qualidade de pesquisa eleitoral (2026-10-26): perguntas sobre eleicoes brasileiras priorizam resultado final, TSE, candidato eleito, votos e percentuais; aumentada a coleta para 8 resultados e reforcado o prompt para nunca declarar ausencia de resultado sem evidencias. Testes Telegram: 42 passaram.
- [x] Pedidos diretos `Abra os meus arquivos` e `Abra o Chrome` agora usam `/pc_open_application`; perguntas sobre eleicoes/fatos atuais usam `/web_search`, com resposta ou erro explicito. Os 40 testes de `tests/test_telegram_bot.py` passaram; o endpoint real de busca retornou fontes do TSE.

#### FASE 30 - Distribuicao
![Em progresso](https://img.shields.io/badge/-EM_PROGRESSO-yellow?style=flat-square)

- [x] `npm install` reproduzivel com `package-lock.json`; `cargo tauri build` gerou `myra-widget.exe` (release)
- [x] Instalador NSIS gerado e smoke-testado: instalacao silenciosa em diretorio temporario, executavel `MYRA` abriu/respondia, desinstalacao concluiu; artefatos temporarios removidos
- [x] Auto-start no boot opt-in por usuario via HKCU Run; menu da bandeja consulta o registro como fonte da verdade e sincroniza a marcacao mesmo em caso de falha; teste real de reboot pendente
- [x] Bandeja do sistema (menu Mostrar MYRA/Sair implementado; smoke visual no Windows pendente)
- [x] Notificacao nativa Windows para conclusao/erro; respeita Nao Perturbe e usa texto generico para nao expor dados da tarefa; smoke test real do toast pendente
- [x] Indicador de conexao no widget (accent conectado; vermelho e tooltip quando API local offline)

#### BACKLOG FUTURO (APOS FASE 30) - App iOS Nativo
![Adiado](https://img.shields.io/badge/-ADIADO%20ATE%20POS%20DISTRIBUICAO-blue?style=flat-square)

**Decisao do usuario (2026-10-26):** nao concluir o iOS nas fases atuais. Preservar integralmente o codigo, projeto Xcode, API remota, Siri e WidgetKit; retomar somente depois da distribuicao da MYRA. Este backlog nao bloqueia a conclusao das fases atuais.

##### Integracao CarPlay (adiada para apos distribuicao)
![Pendente](https://img.shields.io/badge/-PENDENTE-lightgrey?style=flat-square)

**Caminho:** Audio App (aparece como player no CarPlay)

- [ ] Base iOS shell + Tailscale
- [ ] TTS (Piper) + STT (Whisper)
- [ ] CarPlay Audio App framework
- [ ] MPNowPlayingInfoCenter
- [ ] Botoes do volante mapeados
- [ ] Publicacao (opcional: TestFlight)

##### App iOS Nativo e API remota (preservado)
- [x] API Bearer separada: GET /remote/v1/status, POST /remote/v1/task e POST /remote/v1/cancel.
- [x] Token ausente desativa API com HTTP 503; token ausente/invalido retorna HTTP 401; limites de tarefa e conflito cobertos por testes.
- [x] Servidor legado corrigido para escutar em 127.0.0.1, nunca 0.0.0.0 por padrao; verificado apos restart.
- [x] Script scripts/setup_remote_api.ps1 gera token aleatorio de 256 bits e salva no ambiente de usuario Windows.
- [x] App SwiftUI em mobile-ios/MyraMobile: status, envio/cancelamento, HTTPS remoto e token no Keychain.
- [x] AppIntents Siri para enviar tarefa e consultar estado; build CI macOS aprovado em 2026-10-25 (run 40198612123, commit bb87cb41), incluindo o target WidgetKit.
- [x] WidgetKit Home Screen/Lock Screen com estado/progresso, timestamp de atualizacao e sem texto de tarefa sensivel.
- [x] App e Siri rejeitam URLs com credenciais, query/fragmento ou caminho diferente de `/remote/v1`, evitando enviar o Bearer token a uma rota de API diferente.
- [x] Entitlements App Group group.com.myra.mobile incluidos no app e extensao; requerem registro Apple Developer para assinatura/dispositivo.
- [x] Projeto Xcode e workflow macOS de build sem assinatura em .github/workflows/ios-mobile-build.yml.
- [x] Testes direcionados: 41 passed, 1 warning (test_telegram_bot, test_remote_api_auth, test_remote_access); suite completa apos ajuste do fallback de sintese: 1.129 passed, 9 skipped, 31 xfailed, 1 warning e 3.231 subtests (261,91s).
- [x] Build CI do target WidgetKit confirmado no runner macOS (run 40198612123, sucesso).
- [ ] (Pos-distribuicao) Registrar App Group na conta Apple Developer e validar assinatura/instalacao no dispositivo.
- [x] Gerar token remoto aleatorio de 256 bits, salva-lo no ambiente de usuario e reiniciar o backend. Validado em 2026-10-25: `GET /remote/v1/status` retorna HTTP 200 com Bearer correto e HTTP 401 sem token; a API continua vinculada somente a `127.0.0.1:8000`.
- [x] Tailscale Serve HTTPS configurado exclusivamente para `/remote/v1`; testes negativos confirmam HTTP 401 sem Bearer e HTTP 404 para raiz, Telegram, diagnostico local, OpenAPI e docs. Nenhum Funnel ou porta publica foi habilitado.
- [ ] (Pos-distribuicao) Testar status, tarefa, cancelamento, Siri, widget e reconexao no iPhone real via Tailscale. Validacao PC-side via HTTPS/Tailscale: duas tarefas abriram Calculadora e Notepad e chegaram a `done` com UI Automation; tarefa concorrente recebeu HTTP 409 e `POST /remote/v1/cancel` retornou estado `idle`. Ollama foi reiniciado, geracao local validada e sintese LLM normal confirmada na segunda tarefa.
- [ ] (Pos-distribuicao) Implementar/validar APNs push; exige Team ID, chave APNs e registro do dispositivo, ainda nao configurados.

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
| Controle remoto (FASE 28: Tailscale + Telegram) | 100% do escopo ativo | ![100%](https://img.shields.io/badge/-100%25-brightgreen?style=flat-square) |
| CarPlay (backlog futuro apos distribuicao) | ? | Adiado; nao bloqueia as fases atuais |
| Distribuicao (FASE 30) | 6 | ![65%](https://img.shields.io/badge/-65%25-yellow?style=flat-square) |
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

**Checklist PT-BR: 250 itens rastreados**
**Progresso do checklist PT-BR: 37% (92 de 250 itens marcados).**

**Progresso geral combinado dos checklists PT-BR + EN: 33% (160 de 484 itens marcados).**

*Este percentual é a contagem simples dos checkboxes da seção em português; não pondera complexidade nem significa prontidão para produção.*

---

## Proxima acao

**Ordem revisada em 2026-10-22**, apos corrigir os dois bloqueadores da visao:

1. **Concluir a validacao real da FASE 26 no navegador**: navegacao/leitura, scroll, pausa/retomada e clique em `Learn more` foram validados ao vivo. Um formulario local de smoke test tambem passou de ponta a ponta: abriu a URL, preencheu `Your name` com `MYRA`, clicou `Send` e a leitura posterior confirmou `Sent: MYRA`. Corrigidos thread-affinity do Playwright, campos opcionais Pydantic, aliases de argumentos do planner e verificacao de texto esperado apos interacao. A verificacao agora impede que ferramentas irrelevantes apaguem evidencia negativa. Suite completa apos as correcoes de contratos, ferramentas e visualizacao: 1.093 passed, 9 skipped, 35 xfailed, 1 warning e 3.198 subtests (116,07s). O aviso restante e do Starlette TestClient/AnyIO; pendentes: validacao real do widget e triagem dos xfail restantes.
2. **FASE 27.5 (REA):** integracao e smoke tests Ghidra concluidos; analise JavaScript e inspecao estatica Go/Rust do executavel da MYRA passaram. A analise Ghidra completa do binario maior excedeu o prazo do provedor e esta documentada como limitacao, nao como teste aprovado.
3. **FASE 28 (controle remoto: Tailscale + Telegram)**: escopo ativo concluido; usuario confirmou que o Telegram funciona. App iOS, Siri, WidgetKit, assinatura no dispositivo e APNs foram movidos para backlog futuro apos a FASE 30, sem remover codigo nem projeto.
4. **FASE 30 (distribuicao)**: build release, NSIS installer, upgrade da mesma versao em diretorio isolado, uninstall/limpeza do registro e smoke de lancamento do executavel com backend HTTP 200 passaram. Menu/toast visual e reboot real seguem pendentes.

**Ultima validacao automatizada (2026-10-25):** `pytest -q -rxX` — 1.129 passed, 9 skipped, 31 xfailed, 1 warning e 3.231 subtests aprovados (257,05s). O aviso restante vem do Starlette TestClient/AnyIO; os `xfail` restantes continuam em triagem.

**Validacao real atualizada (2026-10-24):** tarefas reais validaram abrir/ler/rolar `https://example.com`, clicar em `Learn more`, pausar/retomar e preencher/enviar um formulario local. O formulario foi confirmado pela leitura do DOM com o texto exato `Sent: MYRA`. Corrigidos thread-affinity do Playwright Sync API, campos opcionais Pydantic, aliases de argumentos de clique e roteamento deterministico para fluxos web compostos com URL. O verificador exige a frase esperada apos a interacao e impede que uma ferramenta irrelevante apague evidencia negativa. Um clique em texto inexistente falha explicitamente, sem sucesso falso nem repeticoes ilimitadas. Suite completa em 2026-10-24: 1.093 passed, 9 skipped, 35 xfailed, 1 warning e 3.198 subtests. A migracao FastAPI lifespan e a API `mss.MSS()` ja estao aplicadas; pendentes: mais testes de recuperacao, triagem de xfail e validacao visual do widget Windows.

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

### PHASE 32 - Native MYRA Workspace, Plugins and Code Studio
![In progress](https://img.shields.io/badge/-IN_PROGRESS-yellow?style=flat-square)

**Goal:** bring core Open WebUI experiences into MYRA's own interface and build a complete coding workspace.

- [x] Individual and bulk conversation selection with per-chat and bulk deletion; native confirmation dialog.
- [x] Convert HTML/CSS/JS answer blocks into a local project with an inline chat preview.
- [x] Import images into Code Studio and drag/drop assets into the preview workspace.
- [x] Composer skill toggles: Code, Research, Design and Review.
- [x] Voice dictation and answer playback using WebView speech APIs.
- [x] Close the widget and overlay when the main desktop window closes.
- [x] NSIS installer bundles Python 3.14, offline core wheels and Playwright Chromium; backend setup installs core dependencies without PyPI downloads.
- [x] Initial plugin reference library and local queue for source review.
- [x] Plugin architecture contract documented in docs/PLUGIN_ARCHITECTURE.md.
- [ ] Secure plugin runtime, manifest validation, capability permissions, install/enable and rollback.
- [ ] Migrate existing Open WebUI tools and skills into the native interface while preserving BrowserAgent and current integrations.
- [ ] Full language editor, console, logs, tests, project tree and responsive preview in Code Studio.
- [ ] Chat image attachments, multimodal files and visual analysis.
- [ ] Local Whisper/whisper.cpp STT and Piper TTS, model selection and audio transcription.
- [ ] Project memory, contextual summarisation, semantic search and retention controls.
- [x] Reorganise backups, context notes, phase reports and patch scripts into dedicated folders while preserving local files.


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

#### PHASE 28 - Remote Control (Tailscale + Telegram)
![Complete](https://img.shields.io/badge/-COMPLETE-brightgreen?style=flat-square)

Detailed status and validation evidence: `PHASE28_MOBILE.md`.

##### 28.1 - Remote access infrastructure (Tailscale)
- [x] Local diagnostic and Windows Tailscale 1.104.2 installed; PC is Running with a Tailscale IPv4.
- [x] Add/authenticate the iPhone in the same tailnet; peer `iphone181` is online at `100.112.204.30` and `tailscale ping` succeeded.
- [x] Validate tailnet connectivity and Serve restricted exclusively to `/remote/v1`; HTTPS status returns HTTP 200 with Bearer, HTTP 401 without it, and root returns HTTP 404. No Funnel/public ports.

##### 28.2 - Telegram Bot
- [x] Long polling, allowlist authentication and commands implemented in `tasks/telegram_bot.py`; no webhook/public API required.
- [x] HTTP 409 polling conflict stops the local poller rather than retrying indefinitely.
- [x] API remains bound to `127.0.0.1`; after the duplicate-poller fix, `/telegram/status` confirmed `running=true` and `last_error=null`.
- [x] User confirmed Telegram is working for now (2026-10-26); monitor operationally and revalidate if the issue returns.
- [x] Regression on 2026-10-26 traced missing replies to HTTP 409 from duplicate polling processes. A Windows mutex keyed by bot-token hash blocks a second instance; after restart `/telegram/status` showed `running=true` and `last_error=null`. A real mutex check confirmed the first instance acquires the lock and the second is blocked.
- [x] `Open my files` and `Open Chrome` route directly to `/pc_open_application`; current-fact/election questions use `/web_search`. On 2026-10-26, fixed a demonstrated synthesis failure where the local model denied a completed election despite matching current-year sources: Brazil 2026 election coverage now triggers a verified TSE-backed deterministic answer, and a regression test proves the model cannot override it. Telegram tests: 43 passed; `py_compile` and `git diff --check` passed. Real Telegram end-to-end response still needs user-side confirmation after service restart.
- [x] General web-research routing (2026-10-26): explicit research intent, current-fact questions and voting-related questions route through web search instead of receiving a generic local-model answer. Replaced election-only synthesis guidance with general evidence-first synthesis: direct answer, cross-checking, source quality, date/context checks, uncertainty disclosure and links. Voting questions get neutral, source-oriented comparison of proposals rather than candidate persuasion. Added routing/synthesis regressions; Telegram tests: 46 passed.

#### PHASE 30 - Distribution
![In progress](https://img.shields.io/badge/-IN_PROGRESS-yellow?style=flat-square)

- [x] Reproducible `npm install` with `package-lock.json`; `cargo tauri build` generated the release `myra-widget.exe`
- [x] NSIS installer generated and smoke-tested: silent install to a temporary directory, `MYRA` executable launched/responded, uninstall succeeded; temporary artifacts removed
- [x] Per-user opt-in auto-start via HKCU Run; toggle in tray menu; state is read from the registry as source of truth and the checkmark is resynchronized after success/failure; real reboot test pending
- [x] System tray (Show MYRA/Quit menu implemented; Windows visual smoke test pending)
- [x] Native Windows notifications on task completion/failure; respects Do Not Disturb and uses generic privacy-preserving text; real toast smoke test pending
- [x] Runtime smoke (2026-10-24): latest release executable launched and remained alive after 5 seconds; UI Automation observed the MYRA window. A real `task_simple` request (`que horas sao`) reached `done` while the widget remained open. Toast appearance is still not visually confirmed; tray-menu visual test and reboot test remain pending.
- [x] Connection indicator in widget (green/accent when connected; red when local API is offline)


#### FUTURE BACKLOG (AFTER PHASE 30) - Native iOS App
![Deferred](https://img.shields.io/badge/-DEFERRED%20UNTIL%20AFTER%20DISTRIBUTION-blue?style=flat-square)

**User decision (2026-10-26):** do not complete iOS in the current phases. Preserve all existing code, Xcode project, remote API, Siri and WidgetKit; resume only after MYRA distribution. This backlog does not block completion of current phases.

##### CarPlay Integration (deferred until after distribution)
![Pending](https://img.shields.io/badge/-PENDING-lightgrey?style=flat-square)

**Path:** Audio App (appears as player in CarPlay)

- [ ] iOS shell base + Tailscale
- [ ] TTS (Piper) + STT (Whisper)
- [ ] CarPlay Audio App framework
- [ ] MPNowPlayingInfoCenter
- [ ] Steering wheel buttons mapped
- [ ] Publishing (optional: TestFlight)

##### Native iOS App and protected API (preserved)
- [x] Bearer-authenticated API: `GET /remote/v1/status`, `POST /remote/v1/task`, `POST /remote/v1/cancel`.
- [x] API disabled without `MYRA_REMOTE_API_TOKEN`; invalid/missing bearer is rejected; task limits and duplicate-task conflict tested.
- [x] Legacy API binds to `127.0.0.1`, not `0.0.0.0` by default.
- [x] SwiftUI app with HTTPS enforcement and token stored in iOS Keychain.
- [x] Siri AppIntents for task submission and status query; app + Siri build passed on macOS CI (run 40197053453).
- [x] WidgetKit Home/Lock Screen extension added; shows state/progress and last-update time without task text.
- [x] Shared App Group entitlements added for app/widget; Apple Developer registration is required for signed device use.
- [x] `scripts/setup_remote_api.ps1` creates a random 256-bit token and stores it in the Windows user environment.
- [x] Focused tests: 40 passed, 1 warning; full Python suite: 1,127 passed, 9 skipped, 31 xfailed.
- [x] Confirm CI build for the WidgetKit extension (run 40198612123, successful).
- [ ] (Post-distribution) Register the App Group in Apple Developer and validate signed installation on device.
- [x] Configure the remote token and restart the backend; HTTPS/Tailscale status returns HTTP 200 with the correct Bearer token and HTTP 401 without it.
- [x] Add iPhone to tailnet and configure Serve restricted to `/remote/v1`; tested that root returns HTTP 404 and protected status returns HTTP 401 without a token.
- [ ] (Post-distribution) Test status/task/cancel/Siri/widget/reconnect on a real iPhone through Tailscale. PC-side HTTPS/Tailscale validation: two tasks opened Calculator and Notepad and reached `done` with UI Automation; a concurrent task was rejected with HTTP 409 and `POST /remote/v1/cancel` returned the state to `idle`. Ollama was restarted, local generation passed, and the second task completed with normal LLM synthesis.
- [ ] (Post-distribution) Implement/validate APNs push; requires Apple Team ID, APNs key and device registration, not yet configured.

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
| Remote control (PHASE 28: Tailscale + Telegram) | Active scope complete | ![100%](https://img.shields.io/badge/-100%25-brightgreen?style=flat-square) |
| CarPlay (future backlog after distribution) | ? | Deferred; does not block current phases |
| Distribution (PHASE 30) | 6 | ![65%](https://img.shields.io/badge/-65%25-yellow?style=flat-square) |
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

**PT-BR checklist: 250 tracked items**
**PT-BR checklist progress: 37% (92 of 250 items checked).**

**EN checklist progress: 29% (68 of 234 items checked).**

*This is a simple count of checkboxes in the Portuguese section; it does not weight complexity or imply production readiness.*

---

## Next action

**Order revised on 2026-10-25 (user decision: defer native iOS installation/polish):**

1. **PHASE 30 Distribution (active):** finish real Windows validation of tray menu, native toast, per-user auto-start after reboot, and clean installer upgrade/uninstall. Native iOS, Siri/WidgetKit device validation, APNs and CarPlay remain preserved in the post-distribution backlog and do not block current phases. Handoff: `HANDOFF_NEXT_CONVERSATION.md`.
2. **Continue PHASE 26 hardening and xfail triage**: live navigation/read/scroll, pause/resume, Learn more click, and a local form flow all passed. The form was filled and submitted, and a subsequent DOM read confirmed the exact Sent: MYRA text. Fixed Playwright thread affinity, optional Pydantic fields, planner argument aliases, deterministic URL/form routing, and verification of expected page text after interaction. A missing-text click fails explicitly; unrelated tools cannot erase negative evidence. Migrated FastAPI startup/shutdown to lifespan and updated the MSS capture API. Latest local unittest suite (2026-10-24): 1,049 tests, exit 0 (9 skipped, 31 expected failures); URL, search-term, click-text, type_text payload, and scroll inputs reject malformed types/values before enqueue; live Chrome Bridge smoke test also passed (`get_tabs` -> open `example.com` -> read DOM/text -> close tab). Remaining: more recovery tests and triage of the remaining xfails.
2. **PHASE 27.5 (REA):** integration and Ghidra smoke tests completed; JavaScript analysis and Go/Rust static inspection of MYRA executable passed. Full Ghidra analysis of the larger binary exceeded the provider deadline and is documented as a limitation, not a passing test.
3. **PHASE 28 remote control (Tailscale + Telegram)**: active scope complete; user confirmed Telegram works for now. Native iOS, Siri, WidgetKit, device signing, APNs and CarPlay are preserved in the post-distribution backlog and do not block current phases.
4. **PHASE 30 distribution**: release x64 build and NSIS bundle generated successfully; isolated silent install/uninstall smoke test passed (exit code 0; executable/uninstaller present and test directory removed). Added cleanup of the per-user MYRA auto-start registry value to the NSIS pre-uninstall hook and rebuilt the installer. Rust auto-start path comparison tests: 3 passed. Validated since the earlier handoff: same-version upgrade in an isolated directory, uninstall registry cleanup, release launch and backend `/task_status` HTTP 200. Still pending: visual tray/toast and actual reboot. Details: `PHASE30_DISTRIBUTION.md`.

**Note:** PHASE 25 (`vision_locate`) is complete and PHASE 24.5 was completed by PHASE 26.

---

**Last updated:** 2026-10-25


## PHASE 32 - Universal Windows Application Access

- [x] 32.1 - Discover app shortcuts from per-user/all-users Start Menu and Desktop.
- [x] 32.2 - Expose app inventory through FastAPI (`POST /pc_list_applications`) and open-app API (`POST /pc_open_application`).
- [x] 32.3 - Register app inventory/open actions as planner tools.
- [x] 32.4 - Open a known shortcut by exact/unique name; reject ambiguous matches.
  - Input validation (2026-10-24): app-open and app-uninstall entry points reject non-string names with a structured error before inventory, registry or PowerShell work; regression tests cover null/list/dict/number inputs.
- [x] 32.5 - Add UI Automation (UIA) control listing with name/type/AutomationId.
- [x] 32.6 - Add controlled UIA actions: click, set text, focus, toggle and select; reject ambiguous/disabled controls.
- [x] 32.7 - Add controlled window actions (minimize/maximize/restore/close) with state verification.
  - Robustness regression (2026-10-24): UIA control/window actions reject non-string action values (including list/dict) with a structured error instead of raising TypeError; tests cover malformed arguments.
- [ ] 32.8 - Validate multi-application workflows with observe-act-verify and recovery.
  - Progress (2026-10-24): deterministic 2-3 app launch flow now requires `pc_open_application` to return `status=ok` before proceeding to the next app.
  - Added post-launch observation through Windows UI Automation: opening is `ok` only when a matching visible window title is observed; otherwise returns `unverified` and explicitly avoids automatic repeat attempts.
  - Automated tests cover verified visible-window success and unverified launch outcomes. Real Windows validation (2026-10-24): the MYRA task opened Notepad and Calculator in sequence, and UI Automation confirmed both visible windows; a separate single-app task opened Calculator and confirmed its visible window. Added Portuguese aliases for "Calculadora do Windows" and "Bloco de Notas do Windows", and stripped a trailing "confirme/verifique..." clause from simple app-opening requests instead of treating it as part of the app name. Remaining: extend post-action observation to click/type/window workflows and validate additional real desktop application types.
  - Window-title matching hardened (2026-10-24): normalizes accents/punctuation and recognizes localized/dynamic titles for Calculator, Notepad, Task Manager, File Explorer and Command Prompt; removed the overly broad raw `cmd` substring match. Six unittest regressions cover localized titles, document suffixes, explicit `cmd.exe`, false-positive rejection and invalid names; all pass.
  - Live Windows UIA smoke test (2026-10-24): matched the actual visible Chrome and PowerShell windows; a background WhatsApp process with no visible window was correctly not treated as a confirmed open window.
  - Additional UI Automation guard: `set_text` and `focus` return success only when their resulting value/focus can be read back; generic click/toggle/select responses explicitly state that the downstream effect still needs observation.
  - UIA state verification extended (2026-10-24): `toggle` returns success only when a readable binary toggle state demonstrably changes; `select` returns success only when the control reports selected. Missing/unreadable state yields `unverified`, so the executor does not repeat the action. Regression tests cover confirmed and unconfirmed state transitions.
  - Click evidence extended (2026-10-24): UIA now returns bounded snapshots of readable control properties before/after a click and a `mudanca_observavel` comparison. A click remains `verified=false` until a downstream observer confirms the actual goal; evidence changes alone are not treated as success. Regression tests cover both unchanged evidence and a changed readable value.
  - Observer evidence handoff (2026-10-24): structured UIA evidence (`mudanca_observavel`, before/after snapshots, `verified`, and status) is now extracted separately into the observer prompt, so long tool results cannot truncate the click-state evidence. The prompt explicitly warns that a state change is not proof of task completion; regression tests cover nested results and long-result truncation.
  - Microsoft Store false-positive guard (2026-10-24): the Telegram Desktop install flow no longer accepts an arbitrary `Open` button as proof when the final control tree does not identify Telegram Desktop. Confirmation requires both a visible/enabled Telegram Desktop identity and a visible/enabled Open/Launch button. Regression tests cover unrelated apps and hidden controls.
  - Store localization hardening (2026-10-24): Telegram identity matching now normalizes accents/case and accepts the package-style `TelegramMessengerLLP.TelegramDesktop` identifier; confirmation recognizes common localized Open labels (including German and French), including the Store's `AcquisitionBlock` Text representation, while still requiring visible/enabled target-specific evidence. Regression tests cover localized labels, package IDs, and non-confirming Install labels.
  - Real Windows Store validation (2026-10-24): live UI Automation showed the exact Telegram Desktop product page, publisher, `OpenInstalledProduct` button and `AcquisitionBlock=Open`. Fixed a control-flow bug where the step-8 result-card click was interpreted as a fresh control list, and allowed one bounded UIA observation after a click even if that listing action was used earlier. Added deterministic synthesis so the LLM cannot contradict the exact product-page evidence. End-to-end MYRA task now completes in 7 steps and reports Telegram Desktop already installed; no extra install was attempted. Targeted regression suite: 213 passed, 3 xfailed, 976 subtests. Fase 32.8 remains open for validation across multiple real desktop app types and other post-action workflows.
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


## Atualização: pesquisa e respostas com evidências (2026-10-26)

- [x] Reforçada a instrução conversacional para evitar recusas genéricas e priorizar a resolução do pedido concreto.
- [x] Perguntas factuais diretas em português e inglês agora acionam pesquisa web sem exigir a palavra “pesquise”.
- [x] Síntese web orientada a cruzar evidências, priorizar fontes primárias, distinguir fatos de incertezas e responder o que for possível.
- [x] Neutralidade mantida em questões eleitorais: comparar propostas e evidências sem escolher pelo usuário.
- [x] 47 testes do Telegram aprovados; compilação Python e `git diff --check` sem erros. A qualidade do modelo em uma conversa real do Telegram ainda precisa de validação prática.


## Correção — troca de modelo no Telegram (2026-10-26)

- [x] Adicionado fallback conversacional: se o modelo escolhido falhar ao carregar ou gerar resposta, MYRA tenta o modelo padrão configurado e informa claramente que usou contingência, evitando silêncio após a troca.
- [x] Teste de regressão cobre falha do modelo selecionado e confirma que o fallback responde.
- [x] Testes Telegram: 48 aprovados; `py_compile` e `git diff --check` concluídos sem erros.


### Correção — pesquisa de alegações eleitorais no Telegram (2026-10-26)
- A busca não deve converter pedidos de evidências sobre suposto golpe/fraude em consultas genéricas sobre o resultado eleitoral.
- Preserva a pergunta original na consulta web e acrescenta termos de checagem factual, evidências verificáveis e fontes oficiais/primárias.
- Adicionado teste de regressão para a pergunta sobre alegação de golpe no segundo turno atribuída ao PT.
- Validação: `tests/test_telegram_bot.py` — 49 testes aprovados.


### Pesquisa investigativa imparcial e cruzamento de fontes (2026-10-26)
- Alegações de fraude, golpe, corrupção, irregularidade ou conspiração acionam três buscas com ângulos distintos: documentos oficiais/judiciais, checagem independente e cobertura jornalística.
- A pergunta original é preservada nas consultas; alegações eleitorais brasileiras acrescentam fontes pertinentes como TSE, auditorias e Ministério Público.
- A síntese deve procurar evidências favoráveis e contrárias, distinguir alegação de fato comprovado, verificar independência entre fontes, datas e contexto, e explicitar incertezas.
- O atalho de resposta pronta sobre resultados eleitorais não pode substituir a investigação quando a pergunta contém uma alegação de fraude/golpe.
- Validação: `tests/test_telegram_bot.py` — 49 testes aprovados; compilação Python e `git diff --check` aprovados.


### Corre??o de evid?ncias, parser de busca e respostas incompletas (2026-10-26)
- Removida a resposta eleitoral pr?-fabricada que inseria nome, votos, percentuais e URL sem deriv?-los da pesquisa real.
- A s?ntese agora instrui explicitamente a usar somente fatos/URLs presentes nos resultados e a rejeitar fontes de outro ano, pa?s, turno ou pleito.
- Aumentado o limite de gera??o da pesquisa para reduzir truncamentos em relat?rios com v?rias se??es; o envio ao Telegram j? divide mensagens longas.
- Substitu?do o parser r?gido de resultados do Google por extra??o HTML que aceita URLs diretas e links intermedi?rios, ignorando markup dentro de scripts.
- A rota `/web_search` tenta o Google como provedor alternativo quando o DuckDuckGo devolve uma p?gina de desafio em vez de resultados.
- Valida??o: `tests/test_telegram_bot.py` e `tests/test_tools_structured.py` ? 189 testes aprovados e 62 subtestes aprovados; `py_compile` e `git diff --check` aprovados.
- Limita??o ainda aberta: teste real em 2026-10-26 mostrou que DuckDuckGo devolve desafio HTTP 202 e Google n?o retorna resultados parse?veis neste ambiente. A rota agora reporta a falha de ambos sem fabricar fontes; o acesso real a um provedor de pesquisa utiliz?vel precisa ser resolvido antes de declarar a investiga??o web conclu?da.


### Pesquisa web: fallback RSS validado no backend (2026-10-26)
- [x] Adicionado fallback estruturado via Google News RSS após falha do DuckDuckGo e do parser HTML do Google.
- [x] Validado no ambiente real: a rota `POST /web_search` retorna HTTP 200 e cinco resultados com título, link e descrição para consulta sobre testes de integridade das urnas no segundo turno de 2022.
- [x] Reiniciado o backend MYRA com segurança para carregar o novo código.
- [x] Regressão: `tests/test_tools_structured.py` e `tests/test_telegram_bot.py` — 190 testes e 62 subtestes aprovados; `py_compile` e `git diff --check` aprovados.
- [x] Corrigido o contexto de perguntas curtas: a pesquisa extrai o tema da primeira frase do pedido longo e o prompt final agora inclui explicitamente o contexto da investigação e a pergunta mais recente.
- [x] Adicionado teste de regressão para a sequência de investigação Covaxin seguida de `Quem é o principal apontado?`; verifica que as consultas continuam no tema e que o briefing inteiro não contamina a busca.
- [ ] Pendente: validar a resposta investigativa completa de ponta a ponta no Telegram, incluindo relevância das fontes, verificação de páginas, datas/contexto e ausência de truncamento. O backend e os testes automatizados passaram; isso ainda não equivale a declarar a resposta final do bot validada.
