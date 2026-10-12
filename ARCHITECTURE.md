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
| `tasks/simple_task.py` | Adaptive planner/executor loop and tool selection. |
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
4. For a browser action, `tasks/browser_bridge.py` validates the action and arguments, writes a command to SQLite, and waits for the extension's completion.
5. The Chrome extension polls the bridge, executes the allowed action in Chrome, then posts the result; the bridge returns it to the planner.
6. For visual interaction, `computer/vision_locate.py` captures/analyses the screen using its OCR/fuzzy-match/LLM pipeline, returns coordinates, and can invoke click/type actions.
7. For local reasoning, the configured LLM is called through Ollama on port 11434. Vision inference is served separately through llm-eyes on port 8081.
8. The planner uses the tool result to decide the next step until it finishes, fails, or reaches the step limit. Task state/events can update the widget.

## Databases and persistence

- **Browser bridge SQLite:** stores queued browser commands and completion results. Default location is under `%LOCALAPPDATA%\MYRA\browser_bridge.sqlite3` (or `~/.myra/browser_bridge.sqlite3` when `LOCALAPPDATA` is unavailable); `MYRA_BROWSER_BRIDGE_DB` can override it.
- **Open WebUI SQLite:** Open WebUI persists its own application data in its configured Docker volume/database. The precise path depends on the container configuration; inspect Docker volumes rather than assuming a fixed host path.
- **Other state:** some features use JSON files or local workspace files, depending on the module.

## Security and operational notes

- Keep the browser bridge token private and configure it consistently for the backend and extension.
- Use local-only networking unless access controls and firewall rules have been reviewed.
- Authenticated browser sessions can perform real actions. Supervise sensitive operations.
- Do not commit credentials, cookies, tokens, or personal data.
- Local model inference does not mean every feature is offline: web search, browsing, YouTube and email need network access.
