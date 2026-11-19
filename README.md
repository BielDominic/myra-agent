# MYRA — Local AI Computer Agent

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Ollama](https://img.shields.io/badge/LLM-Ollama-111111?style=flat-square&logo=ollama&logoColor=white)](https://ollama.com/)
[![Chrome](https://img.shields.io/badge/Browser-Chrome%20MV3-4285F4?style=flat-square&logo=googlechrome&logoColor=white)](https://developer.chrome.com/docs/extensions/)
[![Docker](https://img.shields.io/badge/UI-Open%20WebUI-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docs.openwebui.com/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-0078D4?style=flat-square&logo=apple&logoColor=white)](https://github.com/BielDominic/myra-agent/releases)
[![Status](https://img.shields.io/badge/Status-Active%20development-orange?style=flat-square)]()
[![Repository](https://img.shields.io/badge/Repository-Private-lightgrey?style=flat-square)]()

**MYRA is a local-first personal AI agent designed to do more than answer questions: it can use tools to interact with a browser and desktop, work with files, handle email, assist with code, and carry out multi-step tasks.**

The project combines a locally hosted language model with a FastAPI backend, browser automation, desktop controls, a vision service, and MYRA's native desktop chat and workspace. Existing Open WebUI skills and tools are being migrated through a compatibility layer. The goal is to build a practical computer-use agent whose capabilities can be inspected, developed, and run on a Windows machine.

> **Project status:** experimental and under active development. Capabilities, setup steps, and safety boundaries may change. This README describes the documented architecture; not every feature has the same level of testing or polish.

## Download MYRA

**Latest release: v0.26.3**

- [Windows x64 installer](https://github.com/BielDominic/myra-agent/releases/download/v0.26.3/MYRA_0.26.3_x64-setup.exe)
- [Complete Windows offline setup package](https://github.com/BielDominic/myra-agent/releases/download/v0.26.3/MYRA_v0.26.3_Backend_Setup.zip)
- [Windows SHA-256 checksums](https://github.com/BielDominic/myra-agent/releases/download/v0.26.3/SHA256SUMS.txt)
- [macOS Apple Silicon DMG (arm64)](https://github.com/BielDominic/myra-agent/releases/download/v0.26.3/MYRA_v0.26.3_arm64.dmg)
- [macOS Intel DMG (x64)](https://github.com/BielDominic/myra-agent/releases/download/v0.26.3/MYRA_v0.26.3_x64.dmg)
- [All releases](https://github.com/BielDominic/myra-agent/releases)

**Windows one-click installer:** bundles Python 3.14.10, pinned core wheels, the optional CPU vision/ML wheelhouse (PyTorch, OpenCV, ONNX Runtime, RapidOCR and Ultralytics), and Playwright Chromium. Core dependencies install offline; vision/ML wheels are included but are installed only if the user selects them in the in-app Welcome Setup. On first launch, the user chooses whether to activate vision, install Ollama and download a model, or defer these steps. The same setup remains available under **Primeiros passos**. Model weights are never embedded in the installer.

**macOS:** the DMG is an early-access native desktop shell for Apple Silicon and Intel. Full backend/desktop-automation parity is not yet available; see [INSTALL_MACOS.md](INSTALL_MACOS.md).

## Contents

- [Highlights](#highlights)
- [Capabilities](#capabilities)
- [Download MYRA](#download-myra)
- [macOS installation status](INSTALL_MACOS.md)
- [Windows installation guide](INSTALL_WINDOWS.md)
- [Plugin architecture](docs/PLUGIN_ARCHITECTURE.md)
- [Repository layout](docs/REPOSITORY_LAYOUT.md)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Services and local endpoints](#services-and-local-endpoints)
- [Requirements](#requirements)
- [Getting started](#getting-started)
- [Using the agent](#using-the-agent)
- [Available tool groups](#available-tool-groups)
- [Roadmap](#roadmap)
- [Security and privacy](#security-and-privacy)
- [Development workflow](#development-workflow)
- [Troubleshooting](#troubleshooting)
- [Contributing and project status](#contributing-and-project-status)
- [License](#license)
- [Acknowledgements](#acknowledgements)

## Highlights

- **Multi-step task planning:** the model can choose a tool, review its result, and decide what to do next.
- **Local language model:** inference is provided through [Ollama](https://ollama.com/).
- **Browser automation:** interact with pages, search the web, read page content, and use a dedicated Chrome profile.
- **Desktop control:** mouse, keyboard, window management, and screenshots on Windows.
- **Vision service:** a locally hosted vision model can analyse screenshots and describe visible content.
- **Email and files:** Gmail IMAP/SMTP operations and workspace-focused file tools.
- **Coding assistance:** tools for generating, reviewing, testing, documenting, and analysing code.
- **YouTube workflows:** transcript retrieval, summaries, questions, and saved transcripts.
- **Extensible backend:** FastAPI routes and separate tool modules organise capabilities.

**MYRA is local-first, not universally offline.** Model inference and several services can run locally, but web search, browsing, weather, YouTube, and email require network access when used. External sites and providers remain subject to their own availability and policies.

## Capabilities

### Autonomous task loop

The task planner receives an objective, chooses an available tool, observes the returned result, and continues until it can respond or reaches its step limit. Structured tools are designed to make results easier for the planner to interpret.

The loop implements an observe → act → verify → recover cycle: after each state-changing action an observation is produced, the goal is verified against that evidence (success is not declared without it), failures produce a new-strategy directive with the failed action blocked, and every step is persisted to SQLite so tasks can be paused, resumed, or recovered after a crash. See [ROADMAP.md](ROADMAP.md) for the current status of this work.

Example objectives:
- Search for a topic, open a relevant result, and summarise the page.
- Find a YouTube channel's latest video and report its title.
- Retrieve a video transcript and summarise the main points.
- Check the current time or retrieve weather information.

The planner is experimental. Multi-step execution can fail, choose a suboptimal tool, or require a clearer objective.

### Browser automation

The project includes browser automation and a Chrome extension bridge. Depending on the active implementation and configuration, browser tools can:
- Open URLs and navigate between pages.
- Search Google or DuckDuckGo.
- Read the active tab or page content.
- Inspect structured page data such as links, buttons, and form fields.
- Click elements and enter text.
- Open and close tabs, scroll, wait, and capture screenshots.
- Reuse a dedicated browser profile and its sessions.

Browser actions may affect authenticated sessions. Use a dedicated profile and supervise sensitive workflows.

### Desktop control and vision

Desktop tools provide mouse and keyboard actions, window inspection/focus, and screenshots. The separate vision service can analyse screenshots using a locally hosted multimodal model.

Vision-based interpretation is still evolving; it does not guarantee that an element was identified correctly or that an action succeeded.

### Email

Gmail access is implemented through IMAP/SMTP. Documented operations include listing, reading, searching, sending, replying, marking read/unread, moving, and deleting messages. Some destructive operations are designed to require confirmation.

Email actions can have real-world consequences. Verify recipients and message contents before sending, and review the configured confirmation behaviour before enabling destructive operations.

### Files and coding

File tools support workspace operations such as listing, reading, writing, creating, moving, deleting, and searching files. Coding tools cover generation, explanation, analysis, review, refactoring, optimisation, conversion, tests, documentation, SQL, regular expressions, dependency inspection, linting, metrics, and Python execution.

Treat generated code as untrusted until reviewed. Do not give the agent access to sensitive directories or credentials unless the relevant boundaries are understood.

### YouTube and structured search

The project documents YouTube transcript retrieval, summarisation, question answering, saving and reading transcripts, language selection, and structured search. Other utilities include current time, weather, persistent notes, chart generation, and chat management where enabled.

## Architecture

~~~text
                         User
                          |
                          v
              Open WebUI / MYRA interface
                          |
                          v
                FastAPI backend (8000)
                 /        |         \
                /         |          \
               v          v           v
          Task planner  Tool modules  Task / event APIs
               |          |
               v          +-------------------------------+
        Local LLM via     |               |               |
           Ollama         v               v               v
                       Browser         Desktop          Email/files
                    Chrome bridge    mouse/keyboard    workspace/Gmail
                          |
                          v
                    Chrome session

        Vision service (8081) <--- screenshots
        Ollama service (11434) <--- local model inference
        Open WebUI / proxy (configured locally)
~~~

### Main components

| Component | Responsibility |
|---|---|
| **agent.py** | FastAPI application and API routes |
| **tasks/simple_task.py** | Adaptive planner and multi-step task loop |
| **tasks/structured_tools.py** | Structured search and discovery tools |
| **tasks/browser_bridge.py** | Browser bridge command queue and API routes |
| **tasks/cancel_state.py** | Shared task-cancellation state |
| **computer/controller.py** | Mouse and keyboard automation |
| **computer/screen.py** | Screenshot capture |
| **computer/windows.py** | Window listing and focus operations |
| **browser-extension/** | Chrome Manifest V3 extension and offscreen bridge |
| **tools/browseragent.py** | Open WebUI tool integration for browser/agent capabilities |
| **tools/codeagent.py** | Coding assistant tools |
| **tools/visuals_core.py** | Charts and visualisations |
| **llm-eyes/** | Local vision service and model assets |
| **widget-tauri/** | Desktop widget prototype, where present in the checkout |
| **workspace/** | Working area for supported file operations |

## Technology stack

| Area | Technology |
|---|---|
| Language | Python |
| API | FastAPI, Uvicorn |
| Local model runtime | Ollama |
| Vision inference | llama.cpp / llama-server |
| Chat interface | Open WebUI, optionally behind a local proxy |
| Browser integration | Chrome Extension Manifest V3 and browser automation |
| Desktop automation | PyAutoGUI, MSS, window-management libraries |
| Persistence | SQLite and JSON files in relevant modules |
| Containerisation | Docker Desktop |
| Optional desktop UI | Tauri and Rust |

Exact versions and model choices may differ between machines. Use the dependency files and setup scripts in your current checkout as the source of truth.

## Services and local endpoints

The following are documented defaults. A service may be disabled or mapped to a different port in local configuration.

| Service | Default port | Purpose |
|---|---:|---|
| MYRA FastAPI backend | **8000** | Agent and tool API |
| Vision server | **8081** | Local screenshot/vision inference |
| Ollama | **11434** | Local LLM inference |
| Open WebUI / local proxy | **8082 and/or configured container port** | Chat interface |

Do not expose these services to a public network without reviewing authentication, firewall rules, and the security of each route.

## Requirements

The documented development environment is Windows 10/11. A typical setup may require:

- Windows 10 or 11.
- Python and a project virtual environment.
- Ollama and at least one compatible model pulled locally.
- Docker Desktop for Open WebUI, if using the container-based interface.
- Google Chrome for the browser extension.
- Git for source control.
- Rust and the Tauri toolchain only if developing the optional Tauri widget.
- Sufficient RAM, disk space, and GPU memory for the selected models.

Model performance depends on quantisation, context length, available VRAM, and concurrent services. Choose a model that fits your hardware rather than assuming every listed model can run simultaneously.

## Getting started

MYRA is under active development, and setup details can change. Follow the scripts and configuration files present in your current branch. The commands below are a starting point for the documented Windows layout.

### 1. Obtain the project and prepare the environment

If you have not already cloned the repository:

~~~powershell
git clone https://github.com/BielDominic/myra-agent.git
cd myra-agent
~~~

For an existing local installation using **C:\computer-agent\venv**, activate the environment:

~~~powershell
cd C:\computer-agent
.\venv\Scripts\Activate.ps1
~~~

Install dependencies using the project's dependency manifest, if present:

~~~powershell
python -m pip install -r requirements.txt
~~~

### 2. Prepare Ollama

Install and start [Ollama](https://ollama.com/), then pull the model configured for your installation. The project documentation identifies **qwen2.5:7b** as a primary model in one configuration:

~~~powershell
ollama pull qwen2.5:7b
ollama list
~~~

The model configured in Open WebUI and the model used by the task planner must match your actual setup. Check the local configuration before troubleshooting tool calling.

### 3. Configure secrets and integrations

Configure required values using your local environment or the project's existing configuration mechanism. **Do not commit API keys, bridge tokens, passwords, session cookies, or other secrets.**

The browser bridge uses a shared token in configurations that enable it. Configure the intended token on both the backend and extension. Keep it private and do not expose the bridge to untrusted networks.

For Gmail, configure the supported IMAP/SMTP credentials and authentication method for your account. Prefer provider-supported app passwords or OAuth-based methods where available; never put credentials in the README or source control.

### 4. Start the backend and optional services

Use the scripts that exist in your checkout. The project documentation has included these Windows scripts:

~~~powershell
# Checks/starts local Ollama, then starts the backend
.\iniciar_myra.ps1

# Optional vision service
.\iniciar_visao.ps1
~~~

If you run services manually, start the FastAPI backend from the project environment:

~~~powershell
python agent.py
~~~

Start Open WebUI using the Docker container name configured on your machine. For example, if your container is named **open-webui-custom**:

~~~powershell
docker start open-webui-custom
~~~

### 5. Load the Chrome extension

1. Open **chrome://extensions** in Chrome.
2. Enable **Developer mode**.
3. Choose **Load unpacked**.
4. Select the repository's **browser-extension** directory.
5. Open the extension popup/settings and configure the local API URL and bridge token as required by that version.
6. Check the extension service-worker and offscreen-document consoles if the bridge does not connect.

Extension files and options may change as the browser bridge evolves. Use the manifest and current extension UI as the definitive reference.

### 6. Open the chat interface

Open the local Open WebUI or MYRA proxy address configured for your installation. Select the intended Ollama model and enable the relevant MYRA tool integration. The exact port can differ between the direct container mapping and the local proxy.

## Using the agent

### Example objectives

Use clear, outcome-focused requests. For example:

- “What time is it now?”
- “Search for three reputable sources about local AI agents and summarise the differences.”
- “Find the latest video on this YouTube channel and tell me its title.”
- “Retrieve the transcript of this video and summarise the main points.”

### Call the task API directly

The task route documented by the project is **/task_simple**. Confirm the route and request schema in your current checkout before integrating against it.

~~~powershell
$body = @{
    objetivo = "pesquise três fontes sobre agentes de IA locais"
    max_passos = 15
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/task_simple" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
~~~

Example YouTube transcript request (verify the expected payload in your current API implementation):

~~~powershell
$body = @{ url = "https://www.youtube.com/watch?v=VIDEO_ID" } | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/youtube_transcript" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
~~~

### Pause, inspect and resume a task

Tasks are persisted in SQLite (`%LOCALAPPDATA%\MYRA\myra_tasks.sqlite3`, override with `MYRA_TASK_DB`), so a task can be paused and later resumed without losing the goal, history, observations or recovery attempts. If the process is killed, tasks left `em_execucao` are marked `interrompido` on the next startup and can still be resumed.

~~~powershell
# Pausa a task em execucao (o loop para no proximo ponto seguro)
Invoke-RestMethod -Uri "http://127.0.0.1:8000/task_pause" -Method Post

# Lista tasks retomaveis (pausadas / interrompidas / em execucao)
Invoke-RestMethod -Uri "http://127.0.0.1:8000/task_pendentes" -Method Get

# Retoma uma task persistida, em background
$body = @{ task_id = "task-1234-abcd1234" } | ConvertTo-Json
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/task_resume" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"

# Historico + eventos de auditoria de uma task
Invoke-RestMethod -Uri "http://127.0.0.1:8000/task_detalhe/task-1234-abcd1234" -Method Get
~~~

Task responses from `/task_simple` include `task_id` and `motivo_encerramento`; `status` can be `ok`, `pausado`, `cancelado`, `falhou` or `erro`.

## Available tool groups

The following names are documented by the project. Availability depends on which tool modules are installed, registered, and enabled in your current environment.

<details>
<summary><strong>Browser and structured web tools</strong></summary>

- **browser_get_tabs**
- **browser_read_active_tab**
- **browser_read_page**
- **browser_navigate_active_tab**
- **browser_new_tab**
- **browser_close_tab**
- **browser_type_text**
- **browser_click_text**
- **browser_scroll**
- **browser_wait**
- **browser_search_google**
- **browser_search_google_visivel**
- **search_google_structured**
- **web_search_structured**
- **youtube_search**
- **youtube_channel_latest**
- **get_current_url**
- **read_page_structured**

</details>

<details>
<summary><strong>Desktop</strong></summary>

- **pc_move_mouse**
- **pc_click**
- **pc_double_click**
- **pc_right_click**
- **pc_type_text**
- **pc_press_key**
- **pc_hotkey**
- **pc_scroll**
- **pc_screenshot**
- **pc_get_windows**
- **pc_get_active_window**
- **pc_focus_window**

</details>

<details>
<summary><strong>Email</strong></summary>

- **email_list**, **email_read**, **email_send**, **email_reply**
- **email_mark_read**, **email_mark_unread**, **email_move**, **email_delete**
- **email_search**, **email_delete_by_search**

</details>

<details>
<summary><strong>Code assistant</strong></summary>

- **code_generate**, **code_explain**, **code_analyze**, **code_review**
- **code_refactor**, **code_optimize**, **code_convert**, **code_test**
- **code_document**, **code_diff**, **code_sql**, **code_regex**
- **code_scaffold**, **code_run**, **code_run_file**, **code_benchmark**
- **code_dependencies**, **code_snippet**, **code_readme**, **code_metrics**, **code_lint**

</details>

<details>
<summary><strong>Files, YouTube, and utilities</strong></summary>

**Files**
- **list_dir**, **read_file**, **write_file**, **delete_file**
- **create_dir**, **move_file**, **search_in_files**

**YouTube**
- **youtube_transcript**, **youtube_summarize**, **youtube_ask**
- **youtube_save**, **youtube_list**, **youtube_read**

**Utilities**
- **get_current_time**, **get_weather**, **save_note**, **read_notes**
- Confirmation and cancellation tools where registered
- Vision endpoints such as **/see** and screenshot routes where enabled

</details>

Tool names and counts are not a guarantee: registrations can differ by branch, tool version, and local configuration.

## Repository layout

The following is a conceptual overview; individual files may differ by branch.

~~~text
myra-agent/
├── agent.py                  # FastAPI backend
├── requirements.txt          # Python dependencies, if present
├── tasks/
│   ├── simple_task.py        # Task planner and execution loop (observe/verify/recover)
│   ├── autonomy.py           # Goal verification and failure recovery
│   ├── task_store.py         # Task persistence in SQLite (pause/resume/crash)
│   ├── structured_tools.py   # Structured search and discovery
│   ├── browser_bridge.py     # Browser bridge queue/API
│   └── cancel_state.py       # Shared cancellation and pause state
├── computer/
│   ├── controller.py         # Mouse and keyboard
│   ├── screen.py             # Screenshots
│   ├── observer.py           # Post-action observation (tool result + local LLM)
│   └── windows.py            # Window operations
├── tests/                    # unittest suite for the autonomous loop and task store
├── browser-extension/        # Chrome MV3 extension
├── tools/
│   ├── browseragent.py       # Open WebUI integration
│   ├── codeagent.py          # Coding tools
│   └── visuals_core.py       # Visualisation tools
├── llm-eyes/                 # Vision service and model assets
├── widget-tauri/             # Optional desktop widget, if present
├── workspace/                # Working files for supported file tools
├── ROADMAP.md                # Planned work and project status
└── README.md
~~~

## Roadmap

The roadmap is maintained in [ROADMAP.md](ROADMAP.md). Documented priorities include:

- Improving the planner's direct responses and tool selection.
- Better recovery from tool errors and repeated-action loops.
- Expanding visual observation and verification of completed actions.
- Persisting task state and history.
- Developing a clearer desktop experience and notifications.
- Voice interaction, additional document formats, and broader integrations.
- More comprehensive automated tests, logging, and security controls.

Roadmap entries are plans, not promises or claims that a feature is already implemented. Check the roadmap and commit history for the latest state.

## Security and privacy

MYRA can interact with authenticated browser sessions, files, email, and desktop applications. Treat it as privileged automation software.

- **Keep it local by default.** Do not expose the API, bridge, or vision endpoints to public networks without an explicit security review.
- **Protect tokens and credentials.** Keep secrets in local configuration/environment variables and ensure they are excluded from Git.
- **Use a dedicated browser profile.** This reduces the chance of interfering with personal browsing sessions, but does not remove all risk.
- **Review destructive actions.** Deleting files or email, moving messages, and sending communications can have irreversible consequences.
- **Limit file access.** Keep the workspace boundary enabled and avoid granting access to directories containing sensitive data.
- **Review generated code.** Code execution should be limited to trusted workspaces and reviewed before running.
- **Assume external services receive requests when used.** Websites, search, weather services, YouTube, and email providers may process data needed for those operations.
- **Do not rely solely on model judgement.** Models can misunderstand page content, choose the wrong tool, or report success incorrectly.

Safety controls are still evolving. Verify actual behaviour in your checked-out version before relying on a safeguard.

## Development workflow

Use a feature branch for changes and keep each commit focused. The active development branch documented for this work is **feature/chrome-extension-bridge**; do not assume changes should go directly to **main**.

Before changing code:

1. Inspect the current file and repository status.
2. Back up important files before editing.
3. Preserve UTF-8 encoding without a BOM where required.
4. Run relevant syntax checks and tests after editing.
5. Test runtime behaviour locally before describing it as working.
6. Commit one coherent change at a time.

Useful checks:

~~~powershell
# Python syntax
python -m py_compile .\agent.py

# Autonomous loop / task store test suite (no LLM or network required)
python -m unittest discover -s tests -t .

# JavaScript syntax for the Chrome extension
node --check .\browser-extension\offscreen.js

# Git state
git status
git branch --show-current
~~~

Run checks only for files that exist and were changed. A syntax check does not replace an end-to-end test.

## Troubleshooting

| Symptom | Checks |
|---|---|
| Chat cannot reach MYRA | Confirm the backend is running, the configured URL/port is correct, and the local proxy/container is healthy. |
| Model does not call tools | Confirm the correct model is selected, tool integration is enabled, and the model supports the expected tool-calling format. |
| Browser bridge does not respond | Verify the extension is enabled, API URL and token match, backend is reachable, and service-worker/offscreen console logs show no errors. |
| Vision requests fail | Confirm the vision server is running and the configured model files and endpoint are correct. |
| YouTube transcript fails | Try a valid video URL and check network availability, caption availability, and transcript-service errors. |
| Email operations fail | Verify provider settings, authentication, network access, and account security restrictions. |
| GPU memory errors | Close competing model processes, reduce model/context size, or use a model that fits available VRAM. |

When reporting a bug, include the relevant error, the step that triggered it, the current branch, and versions/configuration involved. Remove tokens, email contents, personal information, and other secrets from logs first.

## Contributing and project status

MYRA is currently a private project in active development. The repository may not accept external contributions yet. For local development, prefer small, reviewable changes with a clear test plan.

Feature requests and bug reports should describe:
- Expected behaviour.
- Actual behaviour.
- Reproduction steps.
- Relevant logs with secrets removed.
- Environment details where relevant.

## License

**No public open-source license has been declared.** The repository is private and licensing terms are to be defined by the project owner. Unless and until a license is added, do not assume permission to redistribute or reuse the code.

## Acknowledgements

MYRA builds on open-source and community tools, including:

- [FastAPI](https://fastapi.tiangolo.com/)
- [Ollama](https://ollama.com/)
- [Open WebUI](https://github.com/open-webui/open-webui)
- [Playwright](https://playwright.dev/)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [PyAutoGUI](https://pyautogui.readthedocs.io/)
- [MSS](https://github.com/BoboTiG/python-mss)
- [Tauri](https://tauri.app/), where used

---

**MYRA — local models, computer-use tools, and an evolving path toward a more capable personal agent.**


## Instalação no Windows

Consulte [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md) para os requisitos, instalação do backend local e configuração da extensão Chrome. Os instaladores x64 serão publicados em [GitHub Releases](https://github.com/BielDominic/myra-agent/releases).
