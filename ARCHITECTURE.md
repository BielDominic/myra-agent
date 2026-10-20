# MYRA — Architecture

## High-level diagram

```text
                         User
                          |
                          v
       +--------------------------------------+
       | Frontend                             |
       | Open WebUI / local proxy             |
       | Tauri widget                         |
       | Chrome MV3 extension                 |
       +------------------+-------------------+
                          |
             chat / tool calls / task events
                          |
                          v
       +--------------------------------------+
       | Backend: FastAPI (agent.py) :8000    |
       |                                      |
       | Routes, confirmation, task state     |
       | /task_simple  /task_status           |
       | /task_cancel  /task_events            |
       | /v1/chat/completions                 |
       +------------------+-------------------+
                          |
             +------------+-------------+
             |                          |
             v                          v
 +---------------------------+  +---------------------------+
 | tasks/                    |  | computer/                 |
 | simple_task.py            |  | controller.py             |
 | structured_tools.py       |  | screen.py                 |
 | browser_bridge.py         |  | windows.py                |
 | cancel_state.py           |  | vision_locate.py          |
 +-------------+-------------+  +-------------+-------------+
               |                              |
               | bridge commands              | screenshots,
               v                              | mouse/keyboard
 +---------------------------+                v
 | SQLite: browser bridge    |       +-------------------------+
 | command queue + results   |       | Windows desktop/apps    |
 +-------------+-------------+       +-------------------------+
               |
       HTTP polling / completion
               |
               v
 +---------------------------+
 | Chrome MV3 extension      |
 | active tab / navigation   |
 | click / type / scroll     |
 +---------------------------+

  agent.py ---- HTTP :11434 ----> Ollama (local LLM)
  computer/vision tools -- HTTP :8081 --> llm-eyes / llama-server
  Open WebUI -- Docker network / local proxy :8082 --> FastAPI :8000
  Open WebUI ---- SQLite volume ----> Open WebUI database

  Optional:
  Tauri widget <---- task state / SSE events ----> FastAPI
```

## Components

| Component | Responsibility |
|---|---|
| Open WebUI | Chat interface and tool integration, usually in Docker. |
| Tauri widget | Desktop mascot/widget and task status UI; optional local build. |
| Chrome extension (Manifest V3) | Executes browser commands in the user's active authenticated browser context. |
| `agent.py` | FastAPI application, API routes, tool registration, task endpoints and OpenAI-compatible chat endpoint. |
| `tasks/simple_task.py` | Adaptive planner/executor loop and tool selection; observe → act → verify → recover cycle with pause/resume support. |
| `tasks/autonomy.py` | Goal verification (`verificar`) and failure recovery (`recuperar`) with blocked-action signatures and explicit limits. |
| `tasks/task_store.py` | Task persistence in SQLite: goal, current step, history, state, timestamps and audit events; enables resume after pause or crash. |
| `tasks/structured_tools.py` | Structured web and YouTube discovery helpers. |
| `tasks/browser_bridge.py` | Token-protected command queue and routes for the Chrome extension; commands/results persist in SQLite. |
| `tasks/cancel_state.py` | Shared cancellation state for tasks. |
| `computer/controller.py` | Desktop mouse/keyboard actions. |
| `computer/screen.py` | Screen capture. |
| `computer/windows.py` | Window listing and focus. |
| `computer/vision_locate.py` | Locates screen elements from descriptions and exposes locate/click/type operations. |
| Ollama | Runs the configured local language model. |
| llm-eyes | Separate local vision inference service. |
| Docker | Runs Open WebUI and supports its local networking/volume persistence. |

## Default local ports

| Port | Service | Connection |
|---:|---|---|
| 8000 | MYRA FastAPI | Local backend API; Docker clients may use `host.docker.internal:8000`. |
| 8081 | llm-eyes / vision server | Local vision inference endpoint, when enabled. |
| 11434 | Ollama | Local LLM inference endpoint. |
| 8082 | Open WebUI / local proxy | Documented local chat entry point; actual Docker port mapping can vary. |

These are documented defaults, not a guarantee that every service is running or mapped to these ports. Check local environment variables, Docker port mappings and launch scripts.

## Request flow

1. The user sends a message through Open WebUI or another configured MYRA interface.
2. Open WebUI calls the FastAPI-compatible endpoint or invokes registered tools.
3. `agent.py` passes a task to `tasks/simple_task.py`, which selects a tool and parses its result.
4. Planner browser actions keep the published browser_* tool names but execute through Playwright wrappers in agent.py, isolated from the user's real Chrome session.
5. The separate Browser Bridge routes remain available to clients that explicitly use them; in that flow, the Chrome extension polls the bridge, executes the allowed action in Chrome, and posts the result.
6. For visual interaction, `computer/vision_locate.py` captures/analyses the screen using its OCR/fuzzy-match/LLM pipeline, returns coordinates, and can invoke click/type actions.
7. For local reasoning, the configured LLM is called through Ollama on port 11434. Vision inference is served separately through llm-eyes on port 8081.
8. The planner uses the tool result to decide the next step until it finishes, fails, or reaches the step limit. Task state/events can update the widget.
9. After each state-changing action, `computer/observer.py` judges the outcome and `tasks/autonomy.py` verifies the goal; failures produce a recovery directive, blocked actions, or an explicit failure reason. Progress is persisted by `tasks/task_store.py`, so a task can be paused (`/task_pause`) and resumed (`/task_resume`) without losing context — including after a crash.

### OpenAI-compatible chat routing

POST /v1/chat/completions is the single chat entry point for the myra-agent model; the Open WebUI Pipe is not required. Ordinary questions use the configured local Ollama chat model, while explicit computer actions go through the existing POST /task_simple route so task state, cancellation, persistence, and widget events remain centralized. The planner keeps the existing browser_* tool names, but their registered implementations use the isolated Playwright browser; the Chrome extension/Browser Bridge remains available through its own routes and is not invoked by planner browser actions. Task status/control and current-time requests reuse existing backend routes. A short local chat history is stored per stable user_id/chat_id under %LOCALAPPDATA%\MYRA\myra_openwebui_chat_memory.json; explicit IDs are read from request metadata/body or headers `X-OpenWebUI-Chat-Id` / `X-OpenWebUI-User-Id`. If the provider omits IDs, MYRA falls back to a fingerprint of the first user message in the supplied history. When the client sends a full conversation, that incoming history takes precedence. Important limitation: if the provider sends only the latest message and omits all conversation IDs, reliable per-chat persistence is impossible; callers should forward a stable chat ID rather than using shared per-user history, which could mix conversations.

## Databases and persistence

- **Browser bridge SQLite:** stores queued browser commands and completion results. Default location is under `%LOCALAPPDATA%\MYRA\browser_bridge.sqlite3` (or `~/.myra/browser_bridge.sqlite3` when `LOCALAPPDATA` is unavailable); `MYRA_BROWSER_BRIDGE_DB` can override it.
- **Task store SQLite:** stores task goal, current step, history, state, timestamps and audit events for pause/resume and crash recovery. Default location is `%LOCALAPPDATA%\MYRA\myra_tasks.sqlite3` (or `~/.myra/myra_tasks.sqlite3`); `MYRA_TASK_DB` can override it (used by the tests).
- **Open WebUI SQLite:** Open WebUI persists its own application data in its configured Docker volume/database. The precise path depends on the container configuration; inspect Docker volumes rather than assuming a fixed host path.
- **Other state:** some features use JSON files or local workspace files, depending on the module.

## Security and operational notes

- Keep the browser bridge token private and configure it consistently for the backend and extension.
- Use local-only networking unless access controls and firewall rules have been reviewed.
- Authenticated browser sessions can perform real actions. Supervise sensitive operations.
- Do not commit credentials, cookies, tokens, or personal data.
- Local model inference does not mean every feature is offline: web search, browsing, YouTube and email need network access.
