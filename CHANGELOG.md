## [0.26.5] - 2026-11-19 — Declarative plugin intake, updater cadence and security hardening

- Added secure local plugin APIs for validating, installing, listing and removing declarative Skills/Prompts. Executable packages, requested permissions and capabilities are rejected; packages remain disabled by default.
- Added streamed ZIP upload limits, path/symlink/duplicate checks, UTF-8 and manifest validation, SHA-256 recording and atomic installation.
- Windows updater now checks for releases every 15 minutes and defers installation while MYRA is active.
- Full test suite: 1,250 passed, 9 skipped, 12 xfailed, 1 warning and 3,250 subtests passed.

## [0.26.4] - 2026-11-19 — Telegram image generation, local image storage, Windows updater and security hardening

- Added per-conversation agent profiles in the native chat (general, senior developer, browser, research, vision and computer control), with agent-specific backend memory namespaces.
- Added image attachments in native chat and Ollama multimodal routing through `MYRA_VISION_MODEL` (default `qwen2.5vl:3b`).
- Added local ComfyUI image generation API and chat action; Telegram supports `/image`, `/imagine`, `/gerar`, `/image_status`, and natural-language image requests, with background generation, provider preflight, image validation and correct photo MIME types. No hosted inference key is bundled.
- Telegram serializes image-generation jobs to protect the 4 GB GPU and queues later requests without blocking chat polling.
- Generated images are validated and stored locally; desktop chat history now keeps a small image URL instead of repeatedly embedding multi-megabyte Base64 payloads, while Telegram still receives the photo bytes.
- Native desktop image requests now opt out of Base64 responses and load the persisted image by local URL; Telegram retains the Base64 response required for its photo upload.
- Added a Windows self-updater watcher launched from the current-user Startup folder; it checks at logon and every six hours, verifies release SHA-256, and defers installation while MYRA is running.
- Restricted local API CORS to trusted Tauri/localhost origins and added an Origin guard against cross-site browser requests; added regression coverage.
- The installed launcher now reloads per-user Telegram, browser-bridge, remote API and CORS settings before backend startup without printing secrets.
- Added hidden ComfyUI launcher/stopper scripts with low-VRAM and CPU-VAE settings for 4 GB GPUs; documented optional local engine installation and startup.
- Added Telegram photo analysis, `/agent`, `/windows`, `/window`, `/apps` and `/open` commands, with explicit confirmation before closing windows.
- Updated the legacy `start.ps1` to launch the native MYRA desktop without requiring Docker/Open WebUI.
- Documented the remaining Open WebUI compatibility boundary and image-generation setup.

# Changelog

Este arquivo segue o formato [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Datas em ISO 8601. O histórico abaixo resume mudanças identificáveis nos commits recentes do repositório; não pretende substituir o histórico Git completo.

## [Unreleased]

## [0.26.6] - 2026-11-19 — Native Plugin Hub UI and Code Studio event fix
- Connected the native plugin library to the local API: import declarative ZIP packages, review manifest and SHA-256, confirm installation, list installed packages and remove disabled packages.
- The UI clearly indicates that imported packages remain disabled and executable third-party plugin runtime is not available.
- JavaScript syntax check passed; Chromium smoke test with a mocked API verified ZIP import, confirmation, disabled state, listing and removal.
- Fixed the missing `id="workbench"` on the Code Studio container, which caused a TypeError and stopped later UI event listeners from registering. The page smoke test then completed without JavaScript errors.
- Live smoke test against the installed backend remains pending until this release is installed.


### Robustez da retomada de tasks (2026-10-22)
- `GET /task_pendentes` rejeita `limite` negativo com HTTP 422 e limita valores maiores que int64 ao maximo suportado pelo SQLite, evitando lista vazia por erro interno.
- Os dois casos de regressao passaram de `expectedFailure` para testes obrigatorios; os seis testes direcionados de limites passaram.

### Correcoes de visao (2026-10-22)
- `computer/vision_locate.py` configura stdout/stderr no uso standalone com `errors="backslashreplace"`, evitando que caracteres OCR fora da code page do Windows interrompam o diagnostico.
- `vision_locate` retorna `status="erro"` quando o OCR nao detecta texto ou nenhum candidato corresponde, impedindo o planner de contabilizar alvo ausente como acao bem-sucedida.
- `vision_click` e `vision_type` validam respostas incompletas/legadas e rejeitam alvo ou coordenadas ausentes antes de agir. Foram adicionados testes de regressao e tres antigos `xfail` passaram a testes normais aprovados.
- `_coordenadas_para_mouse()` agora valida limites da tela antes de clicar ou digitar, inclusive quando uma resposta antiga nao traz dimensoes do screenshot; coordenadas negativas, fora da tela ou absurdas falham de forma estruturada sem chamar o mouse.
- `vision_locate()` rejeita tipos invalidos para descricao e caminho do screenshot com erro estruturado, em vez de deixar `AttributeError`/`TypeError` escapar do executor.
- `tasks/simple_task.py` agora observa `browser_read_page` e `browser_read_active_tab`; `tasks/autonomy.py` impede sucesso prematuro quando navegar nao cumpre pedido de leitura, quando ler nao cumpre pedido de clique/digitacao, ou quando uma extracao nao traz texto do corpo da pagina. A sintese final `responder` nao apaga evidencia de falha da ultima acao real.
- `browser_wait` aguarda com `time.sleep` limitado a 30s sem reabrir/recriar o perfil persistente do navegador.
- Suite completa atualizada apos as correcoes de limites e regressao: `pytest -q` — 1.017 passed, 9 skipped, 52 xfailed, 79 warnings e 2.907 subtests aprovados (148,87s).
- Integracao opt-in: 9 testes passaram com backend, Ollama, servidor de visao e Browser Bridge ativos. Uma task real de dois passos via `/task_simple` abriu `https://example.com`, leu o corpo da pagina e extraiu `Example Domain` e o primeiro paragrafo. O verificador deterministico impediu sucesso prematuro apos a navegacao; recuperacao e pausa/retomada reais continuam pendentes.

### Roadmap e validacao (2026-10-20)
- Auditoria do `ROADMAP.md`: progresso atualizado para 32% por contagem simples dos checkboxes em portugues (76/241); o valor anterior de 72% nao correspondia ao checklist verificavel.
- FASE 27 (Overlay Visual TARS) marcada como concluida no roadmap, com base nos sete itens implementados e nos testes de contrato/integração existentes.
- FASE 26 permanece em progresso: adicionados como pendentes os dois problemas de visao/encoding identificados nos testes.
- Suite completa executada: `pytest -q` — 997 passed, 9 skipped, 60 xfailed, 79 warnings e 2.905 subtests aprovados. Os testes xfailed continuam precisando de triagem; teste automatizado nao substitui validacao real no navegador, Telegram, Tailscale e iOS.


### Added
- Roteamento central do myra-agent em /v1/chat/completions; o Pipe MYRA Local foi removido do Open WebUI.
- Memória curta por conversa, separada por user_id/chat_id, armazenada localmente em %LOCALAPPDATA%\\MYRA\\myra_openwebui_chat_memory.json.
- Testes de roteamento, separação de memória, IDs explícitos e encaminhamento de identidade por headers.

### Changed
- Ações explícitas chamam a rota existente /task_simple em thread, mantendo um único ciclo de task, persistência, cancelamento e atualização do widget.
- Os 12 nomes browser_* existentes foram preservados, mas suas implementações no registro do planner agora usam Playwright isolado; a extensão/Browser Bridge continua disponível pelas rotas próprias, fora do fluxo do modelo.
- Chamadas internas ao backend e ao Ollama não bloqueiam o event loop.

### Fixed
- **Segurança — path traversal nas rotas de ficheiros:** o guard usava `os.path.abspath(destino).startswith(os.path.abspath(WORKSPACE_DIR))`, que aceita prefixos irmãos (`..\workspace_evil\x`) e permitia ler, escrever, mover e apagar ficheiros fora do workspace. Substituído por `agent.caminho_no_workspace()`, que usa `os.path.commonpath` (7 pontos de uso: list_dir, read_file, write_file, delete_file, create_dir, move_file, code_run_file).
- **Robustez — unicode no stdout:** imprimir um emoji (ex.: nome de ficheiro vindo do planner) levantava `UnicodeEncodeError` com a consola cp1252 e derrubava a rota com HTTP 500. `stdout`/`stderr` passam a ser reconfigurados para UTF-8 com `errors="replace"` no arranque do `agent.py`.

### Added
- `tests/helpers.py` — infraestrutura dos testes severos: `AmbienteIsolado`, `workspace_temporario`, `sem_rede`, `HTTPFalso`, `cliente_agent`.
- `tests/test_seguranca_paths.py` — 20 testes severos de contenção de caminhos (travessia, prefixo irmão, caminho absoluto, unicode/emoji, entradas degeneradas).
- `tests/test_integracao_optin.py` — camada 3 de testes reais, desligada por omissão (`MYRA_TEST_INTEGRATION=1`); valida Ollama, backend, serviço de visão, bridge (token) e ferramentas de leitura, sem efeitos destrutivos.
- `requirements.txt` passa a declarar todas as dependências realmente usadas (youtube, visão/OCR, controlo de PC, widget), agrupadas por área.



## [2026-10-15]

### Added
- **FASE 26 — verificacao:** `tasks/autonomy.py::verificar()` decide se o objetivo foi atingido com base em evidencia observavel; sem evidencia o resultado e `indeterminado` e o sucesso nunca e declarado.
- **FASE 26 — recuperacao:** `tasks/autonomy.py::recuperar()` sugere nova estrategia por ferramenta, mantem acoes bloqueadas por assinatura e aplica limites explicitos (`MAX_TENTATIVAS_POR_ACAO`, `LIMITE_RECUPERACOES`).
- **FASE 26 — persistencia:** `tasks/task_store.py` (SQLite, `%LOCALAPPDATA%\MYRA\myra_tasks.sqlite3`, configuravel por `MYRA_TASK_DB`) grava objetivo, passo atual, historico, estado, timestamps e eventos de auditoria.
- **FASE 26 — pausa/retomada:** rotas `POST /task_pause`, `POST /task_resume`, `GET /task_pendentes` e `GET /task_detalhe/{task_id}`; `retomar_task()` continua do passo seguinte preservando historico, observacoes, verificacoes e recuperacoes.
- **FASE 26 — retomada apos crash:** no startup o agent marca como `interrompido` as tasks `em_execucao` de execucoes anteriores (comparacao por `run_id`) e permite retoma-las.
- Testes em `tests/` (43 testes, `unittest` da biblioteca padrao): persistencia, verificacao, recuperacao, ciclo completo, pausa/retomada, retomada apos crash, cancelamento e rotas HTTP.

### Changed
- `executar_task()` aceita `task_id`, `historico`, `passo_inicial` e `persistir`, devolve `task_id` e `motivo_encerramento` e passa a ter os estados `pausado` e `falhou`.
- O planner recebe `DIRETRIZ DE RECUPERACAO` e `ACOES BLOQUEADAS`; o loop recusa `finalizar` quando existe evidencia forte de falha (no maximo 2 recusas).
- `tasks/cancel_state.py` controla tambem a pausa (`marcar_pausada`, `resetar_pausa`, `esta_pausada`).
- `MAX_ERROS_CONSECUTIVOS` deriva de `LIMITE_RECUPERACOES + 1` para que o motivo explicito da recuperacao seja o que encerra a task.
- Roadmap: FASE 26 em progresso (80%), progresso declarado 72%.

## [2026-10-12]

### Added
- **FASE 25 concluída — visão com coordenadas:** módulo `computer/vision_locate.py` com fuzzy matching e fallback LLM.
- Rotas `/vision_locate`, `/vision_click` e `/vision_type` no backend.
- Três ferramentas visuais integradas em `tools/browseragent.py` e regras de seleção no planner.

### Changed
- O planner recebeu instruções para escolher as ferramentas `vision_*` quando precisa localizar ou interagir com elementos visíveis sem seletor DOM.
- Roadmap bilingue atualizado: FASE 25 concluída; progresso declarado em 70%; próxima fase ativa é a 26.

### Fixed
- Remoção de duplicação das rotas visuais após patch repetido, conforme commit `dddac46`.
- Polling da extensão Chrome serializado com `setTimeout` recursivo e guarda `pollRunning`, evitando acumulação de polls.
- Estado de conclusão/cancelamento de tarefas ligado ao widget, conforme commits recentes.

## [2026-10-11]

### Added
- README de projeto com arquitetura, setup, grupos de ferramentas, segurança e troubleshooting.
- Melhorias do widget Tauri para passos, tema, modo compacto, bloqueio e cancelamento real de tarefas.
- Ferramenta de pesquisa Google visível na extensão/bridge.

### Changed
- Polling da bridge alterado para execução serializada e menos atrasos de scroll.

### Fixed
- Correções no ciclo de polling para evitar múltiplas execuções concorrentes.
- Melhorias no cancelamento real de tasks e na comunicação de estado para o widget.

## Histórico de commits de referência

- `8bc41fc` — `feat(vision): vision_* no tools/browseragent + regras no planner`
- `dddac46` — `feat(vision): rotas /vision_locate, /vision_click, /vision_type + planner`
- `12e9871` — `feat(vision): vision_locate com fuzzy match + LLM fallback`
- `0220841` — `merge: ROADMAP bilingue com badges`
- `b33061b` — `docs: roadmap completo bilingue (PT/EN) com badges, fases 25-31`
- `2a97ef` — `merge: README profissional + widget + cancelamento de tasks`
- `e7a5875` — `feat(widget): bloco A (passos, tema, compacto, trava, pausa UI) + cancelamento real de tasks`
- `7103b03` — `feat(bridge): browser_search_google_visivel + fix polling serializado`
- `67f47ac` — `fix(offscreen): polling serializado com setTimeout recursivo + guarda pollRunning`

## [0.26.2] - 2026-11-19

### Windows installer
- Bundled the default CPU vision/ML stack offline: PyTorch, TorchVision, OpenCV, ONNX Runtime, RapidOCR and Ultralytics.
- Expanded installer smoke tests to import the complete vision stack and run Playwright Chromium.
- Added first-run Ollama setup with selectable local models and a skip/defer option.
- Aligned chat, code generation and task planner model defaults with the selected installed model.
- Created per-Windows-user profile metadata and isolated workspace folders for projects, downloads, artifacts and memory.

### macOS
- Added native Tauri DMG build workflows for Apple Silicon and Intel.
- Added macOS URL opening, Chrome activation and local task-status/cancel IPC support in the desktop shell.
- Documented the macOS build as early access; backend desktop automation parity remains incomplete.


## [0.26.3] - 2026-11-19

### Welcome Setup and prompt refinement
- Added a first-run Welcome Setup inside the MYRA desktop workspace, with a persistent **Primeiros passos** navigation tab for later changes.
- Changed Windows setup to install only core dependencies automatically. Vision/ML wheels remain bundled offline but are installed only after explicit opt-in.
- Added local setup status, optional offline vision installation, opt-in Ollama installation through winget, and selectable local model download.
- Removed the separate blocking WinForms model wizard from the installer flow; setup choices now live in the MYRA interface.
- Added a prompt improver beside the chat composer. It uses the configured local model and returns an editable draft; it never sends the improved prompt automatically.
- Added local-only guards to setup endpoints and documented first-run choices, model download, and per-user workspace behavior.
