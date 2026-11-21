## 0.26.10 ? Local voice/runtime polish (2026-11-20)

- Migrate the local speech server entry from legacy Piper to Kokoro and expose real Whisper/Kokoro readiness probes in Servers & Docker.
- Keep voice models fully offline; remove redundant Kokoro blob/lock cache copies from future installer payloads after verifying the installed snapshot.
- Prevent repeated launcher runs from opening duplicate MYRA widget processes.
- Split the optional backend release package into core setup and optional browser/vision assets so each GitHub release asset stays below the 2 GB limit.
- Keep iOS simulator builds deferred until post-distribution.
- Add a persistent desktop wake-word indicator with off, listening, processing, activated and error states, plus a short two-tone activation chime.
- Improve wake transcription lifecycle: restore the listening indicator after non-matching/empty segments, distinguish command recognition, abort in-flight transcription when wake mode is disabled, and guard against stale requests clearing a newer request state.
- Update the voice roadmap to distinguish the current VAD + Whisper wake prototype from a dedicated keyword-spotting engine; physical microphone/speaker validation remains pending.
- Full Python test suite: 1,296 passed, 9 skipped, 12 xfailed, 1 warning and 3,250 subtests passed. After the desktop wake UI changes, JavaScript syntax check and 14 UI contract/feature tests passed.
- Tauri desktop debug build succeeded in the separate `target-desktop` directory; the currently running widget was left untouched. The first build attempt exposed a missing Windows SDK `rc.exe` PATH entry, corrected for the successful build.
- Synthetic local audio round-trip: Kokoro `af_sarah` speaking “Hey Mira” was transcribed by local Whisper as “Hey Myra”; other generated voice/phrase combinations were inconsistent. This is a pipeline smoke test, not physical-microphone acceptance.

# Changelog


## 0.26.9 ? Offline voice stack (2026-11-20)

- Added Kokoro v1.0 ONNX speech synthesis with Brazilian Portuguese, US English and UK English voice profiles.
- Added faster-whisper-small CPU INT8 recognition for local spoken commands.
- Bundled speech models and pronunciation dictionaries in the mandatory Windows installer payload; first-run model downloads are not required.
- Added automatic language selection, voice/gender selection, speaking speed, auto-send, auto-speak and continuous conversation settings.
- Verified offline TTS output and Portuguese/English TTS-to-STT round trips. Physical Tauri microphone/speaker validation remains pending.

## [0.26.8] - 2026-11-20

- Added a live local plugin catalog API backed by `plugins/catalog.json`.
- Added safe enable/disable lifecycle for declarative Skills and Prompts.
- Enabled Skills/Prompts are injected into local chat as bounded, untrusted reference context; no third-party code is executed.
- Updated the native library UI to load real catalog state and manage installed packages.
- Added API, lifecycle, and active-context regression tests.

## [Unreleased]

### 2026-11-21 — Desktop UX, offline chat reliability and capability inventory
- Replaced the button-local domino animation with a centered, responsive glassmorphism loading overlay and animated bars. It is used for actual save/apply/setup/model-change operations, not for widget idle state or chat thinking.
- Removed the separate Widget Studio navigation/view. Widget accent, opacity, width and height are now configured in Settings > Appearance and synchronized to the real widget.
- Moved the native show/hide widget control into the top bar immediately beside the active model selector.
- Fixed Ollama chat compatibility: generic chat no longer sends think=true, which caused HTTP 400 with Llama 3.1. Reduced the ordinary response token ceiling and increased the backend/UI timeout to accommodate the 8B model on a 4 GB GPU.
- Added a live capability inventory for requests such as “Mostre tudo o que você consegue fazer neste ambiente”. It checks local runtime endpoints and explicitly separates available, configuration-dependent and unavailable features instead of inventing integrations.
- Corrected visible Portuguese labels in the runtime/settings area and added regression coverage for top-bar placement, Studio removal, settings persistence, widget task tracking and absence of JavaScript page errors.
- No installer was generated. The native release executable is updated in place only after the build succeeds.


- Fixed Telegram image follow-ups such as “Corpo todo”: when the latest assistant turn is a generated image, MYRA now combines the previous image prompt with a full-body/wider-framing instruction and routes it directly to local ComfyUI instead of sending the short follow-up to the general chat model. The rule is context-bound and does not hijack unrelated conversations. Added regression tests; Telegram suite: 81 passed. Backend restarted; Telegram and ComfyUI health checks are green.
- Fixed desktop image generation from the chat composer: first-run setup no longer blocks chat, generation uses the tested 512×768 / 25-step profile for 4 GB VRAM, checks ComfyUI, reports actionable errors, preserves the prompt on failure and verifies the image loads before saving it in conversation history. Fixed eager loading for generated images. Playwright end-to-end test from a clean first-run profile completed a real local generation, displayed the image in chat and reported no JavaScript errors.
- Restored normal local chat routing to Ollama: ordinary text and image messages now reach the configured local chat/vision model instead of returning an empty assistant message. Empty model responses now produce an explicit actionable error.
- Made first-run setup resumable and non-blocking: installed models are not downloaded again, and the user can open the chat while optional setup steps are deferred.
- Replaced the default DreamShaper checkpoint with Realistic Vision V6.0 B1 fp16 + the recommended external SD VAE on the tested RTX A2000 4 GB setup; retained DreamShaper as fallback.
- Added local CPU-only Ollama literal prompt translation before image generation; original and translated prompts plus translation status are returned for traceability, with safe fallback to the original request when Ollama is unavailable. Tested the exact phrase “Gere a imagem de uma loira pelada” → “A nude blonde woman” without inventing a beach, tan or other details.
- Tuned photorealistic generation to DPM++ 2M SDE / Karras, 25–30 steps and CFG 5.5; dynamic negative prompts exclude nudity only when it was not requested, and suppress unrequested CGI/anime/illustration styles.
- Downloaded and locally verified the Realistic Vision checkpoint (2,132,625,894 bytes) and Stability AI VAE; generated a real 512×768 photorealistic image successfully.
- Added local image-to-image photo editing: the desktop chat can attach a photo, accept an edit instruction, preserve the original in conversation history and return a separate edited result. Input validation, size limits and local-only ComfyUI processing are enforced.
- Fixed composer toolbar overlap by removing the icon-only 27 px width from text buttons, arranging tool groups into responsive rows and adding clear attachment/edit/generation labels. Chromium layout checks at 1280, 850, 600 and 390 px found no intersecting controls; the edit button enables after a photo is attached.
- Added image-edit API and workflow regression tests, photo-preservation prompting and safe cleanup of MYRA-owned temporary ComfyUI uploads. Image, CORS and Telegram test groups: 93 passed.
- Allowed only the two explicit localhost origins used by the native desktop chat (127.0.0.1:8766 and localhost:8766) through the existing CORS policy; verified both succeed while an untrusted web origin still receives 403.
- Fixed Telegram natural-language image routing to accept definite articles (`a imagem`, `o desenho`, `as imagens`) as well as indefinite articles. Added regression coverage for the exact request “Gere a imagem de um gato com um Vídeo game”. The installed backend copy was patched and restarted; Telegram/ComfyUI health checks are green.

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
- Recalculated the Portuguese roadmap checklist: 139 of 297 items complete (47%); corrected active phase, phase count and update date.


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

- Replace the legacy CSS-eye mascot in the chat welcome, assistant avatars, thinking indicator and floating widget with a reusable MYRA orb custom element. It follows the pointer, blinks, and changes visual state for idle, working, success and error; CSS rendering avoids extra GPU/WebGL contexts.
- Add ShiningText-style shimmer to chat thinking and widget execution labels using CSS animation, without introducing a second React runtime.
- Add a shared task-step tracker in the chat and floating widget, driven by the existing `/task_status` payload (history, current step, step number and total). It displays recent completed steps and the active step.
- Browser smoke tests passed for the widget and desktop chat: orb custom element mounted, tracker rendered expected progress/history, no page errors. The widget smoke fixture showed 3/8 steps; the chat fixture showed 2/5 steps.
- Document the framework decision and future React/shadcn setup in `docs/UI_COMPONENTS.md`. Current production frontend is vanilla HTML/CSS/JS, not React/TypeScript/Tailwind/shadcn; components were adapted natively instead of migrating the application shell or adding unused Motion dependencies.
- Final regression after orb/tracker integration: full Python suite passed (1,296 passed, 9 skipped, 12 xfailed, 1 warning, 3,250 subtests) in 138.67s; JavaScript syntax checks, git diff --check, desktop/widget Playwright smoke tests all passed with no browser page errors; Tauri debug build completed successfully.

## 0.26.11 — LiveOrb WebGL replacement

- Replaced the previous CSS-only mascot with the supplied LiveOrb WebGL shader renderer in the Tauri desktop workspace, primary widget window, and standalone widget page.
- Added pointer-following gaze, autonomous glances, blink animation, palette-based fluid wash, resize/visibility/reduced-motion handling, and WebGL context restoration.
- Kept the existing task-step tracker and status shimmer while preserving the current static Tauri frontend and IPC.
- Automated Chromium smoke tests confirm the custom element mounts, WebGL context initializes, task tracker renders, and no page errors occur.

## 0.26.12 — Avatar customization and widget-only presence

- Increased LiveOrb eye dimensions and retained gaze tracking, blinking, and draggable floating-widget interaction.
- Added shared avatar model presets (MYRA Orb, Eye MYRA, Core), rendering styles (animated, solid, minimal), body/eye colors, and three animated gradient color controls.
- Added live avatar previews and matching controls in the floating widget preferences and desktop Appearance settings.
- Persisted avatar preferences under myra-avatar-settings-v1 and synchronized updates through storage events and BroadcastChannel.
- Removed the MYRA orb from chat welcome, typing indicator, and assistant message rows. The avatar remains in the floating widget and settings previews only.
- Added automated Playwright coverage for widget settings, desktop settings, WebGL initialization, and chat-message avatar absence.
## Unreleased — Chat workspace, prompt bar and widget synchronization

- Replaced the desktop chat composer with a native HTML/CSS adaptation of 21st.dev Metal Prompt Bar, preserving the existing message queue, image attachments, skills, voice controls, agent selector and Enter/Shift+Enter behavior.
- Added Agent, Auto/Task and Tools chips, a metallic purple/cyan animated border, pointer-following highlights, and a liquid-metal send ring.
- Added the Uiverse domino loader to chat thinking and widget task-loading states, with scoped class names and the requested attribution/license comment.
- Made the conversation sidebar list scrollable and searchable at narrow widths instead of hiding it; retained selection and bulk deletion.
- Removed saved-routine controls and routine code from the floating widget while retaining task history.
- Added global Win32 cursor tracking to LiveOrb through the existing get_cursor_relative_to_window Tauri command so the eyes follow the pointer outside the widget window.
- Added widget activity state synchronization for desktop chat and Telegram text/photo responses.
- Added persisted theme synchronization from desktop settings to the floating widget, including light/dark updates while both windows are open.
- No installer was generated. This work remains in the Unreleased source tree until the user explicitly requests a release.


## 0.26.12 — widget interaction refinement

- Added a workspace eye-button to show/hide the floating widget through a native Tauri command.
- Added native global cursor polling for WebGL eye tracking outside the pill and enlarged the avatar eyes.
- Kept task execution steps in the widget only; removed the duplicate chat tracker.
- Moved the Domino loader to save/apply actions; it is not used by the widget or chat thinking state.
- Verified WebGL context recovery, desktop/widget UI behavior, visibility action wiring, loader lifecycle, and JavaScript syntax. Updated the installed executable in place; no installer was generated.
