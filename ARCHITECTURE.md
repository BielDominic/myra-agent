# MYRA ? Architecture (native desktop baseline)

## Product boundary

The supported product entry point is the native Tauri desktop application (`src/desktop.html`, `src/desktop.js`) backed by the local FastAPI service (`agent.py`). Docker and Open WebUI are not required for installation, startup, chat, or the local workspace. `start.ps1` now delegates to the native desktop launcher.

A legacy compatibility boundary remains: `/v1/chat/completions` keeps an OpenAI-compatible request/response shape but is implemented by MYRA; old Open-WebUI-specific chat-history routes (`/pc_get_chats`, `/pc_remove_chat`, `/pc_remove_chats_by_search`, `/pc_remove_all_chats`, `/pc_rename_chat`) and `_owui_request` still call an optional Open WebUI instance. The native desktop does not use those routes. Legacy docs and environment names are being retired separately; do not configure Docker just to use MYRA.

## High-level architecture

```text
MYRA Desktop (Tauri) ??????? Telegram Bot (allowlisted chats)
          ?                         ?
          ???????????????????????????
                     ?
          FastAPI / Orchestrator (127.0.0.1:8000)
          ??? Chat + per-chat agent profiles/memory
          ??? Task planner, queue, pause/resume, audit
          ??? Application/window/UI Automation
          ??? Browser Bridge + Playwright tools
          ??? Files, code, email, plugins, integrations
          ??? Image/vision routing
               ?           ?              ?
               ?           ?              ?
            Ollama     ComfyUI local    Chrome extension
          (11434)      (8188 optional)  (authenticated bridge)
```

## Main modules

| Module | Responsibility |
|---|---|
| `src/desktop.html`, `src/desktop.js` | Native chat, workspace, per-conversation agent selector, image attachments and local image generation action. |
| `agent.py` | FastAPI routes, local chat routing, task state, tool registration and compatibility APIs. |
| `tasks/simple_task.py` | Planner/executor loop, tool selection, observation, verification and recovery. |
| `tasks/telegram_bot.py` | Allowlisted Telegram polling, task commands, per-chat agent profiles, photo input and generated-image delivery. |
| `tasks/browser_bridge.py` | Authenticated browser command queue and Chrome extension bridge. |
| `tasks/system_tools.py` | Planner-facing system, application, window and UIA tools. |
| `computer/applications.py` | Safe application inventory and launching. |
| `computer/ui_automation.py` | Enumerate controls and interact with windows; minimize, maximize, restore and close. |
| `computer/image_generation.py` | Local ComfyUI workflow submission, polling and generated image retrieval. |
| `computer/vision_locate.py`, `computer/observer.py` | Visual targeting and action outcome observation. |
| `src-tauri/` | Desktop shell, window lifecycle and native commands. |

## Local services

| Port | Service | Required? |
|---:|---|---|
| 8000 | MYRA FastAPI | Yes |
| 11434 | Ollama | Yes for local LLM chat |
| 8081 | llm-eyes / vision service | Optional; legacy visual pipeline |
| 8188 | ComfyUI | Optional; local image generation |

## Agent isolation

The desktop stores an `agentId` on each conversation and sends it in request metadata. Backend memory keys are namespaced by both conversation and agent, preventing the same chat's general, developer, browser, research, vision and computer contexts from being merged. Telegram stores an agent selection per Telegram chat via `/agent`. Tools remain shared capabilities, but each agent receives a distinct system profile.

## Multimodal input and image generation

Image attachments are resized in the native client and passed as OpenAI-compatible `image_url` parts. The backend converts supported data URLs to Ollama `images` input and uses `MYRA_VISION_MODEL` (default `qwen2.5vl:3b`). This model must be installed locally.

Image generation is local-first through ComfyUI at `http://127.0.0.1:8188`. MYRA submits a text-to-image workflow using a checkpoint already installed in ComfyUI, then returns the generated image to the chat or Telegram. No hosted generation API key is bundled. Image quantity is not capped by MYRA; available disk, memory, GPU and ComfyUI resources remain practical limits. See `docs/IMAGE_GENERATION.md`.

## Security boundaries

- The backend launcher binds to loopback (`127.0.0.1`); do not expose it to a LAN or the public internet without authentication and firewall review.
- Browser CORS is restricted to the native Tauri origins and local development origins. An Origin guard rejects untrusted browser origins even for simple requests; add a trusted browser-extension origin explicitly through `MYRA_CORS_ORIGINS` when required.
- Telegram commands are restricted to `allowed_chat_ids`; never enable an empty or broad allowlist.
- Browser Bridge uses a bearer token. Keep it private and rotate it if exposed.
- App/window actions target a unique window and verify the resulting state. Closing windows can discard unsaved work and must be explicitly confirmed.
- Treat webpage contents, files, images and model outputs as untrusted input.
- Image models and ComfyUI workflows run locally; only use checkpoints and custom nodes from trusted sources.
- API credentials belong in local environment/config files, never in Git.

## Known gaps (not yet full parity)

- Windows has the deepest desktop automation support. macOS native packaging exists, but full app/window/UI Automation parity is not yet complete.
- Playwright and Chrome extension control are separate execution contexts; the planner must identify which browser session is being controlled.
- Not every app exposes accessible UI Automation controls; visual fallback and per-app adapters remain necessary.
- Native chat history is currently local to the desktop profile; multi-device sync and robust large-attachment storage are not yet complete.
- Open WebUI-specific history compatibility routes and legacy manuals still need retirement.
- Security needs a complete permission model, per-tool approvals, secret vault, rate limits, and structured audit UI.



## Local runtime, Docker and voice (2026-11-20)

The native desktop includes an optional local Docker manager for Ollama and SearXNG, loopback endpoint checks, server/channel preferences and allowlisted container actions. Windows desktop automation stays on the host; Docker is not required for the core app.

Voice input/output is now packaged in the mandatory offline installer: Kokoro v1.0 ONNX for natural speech synthesis (pt-BR, en-US, en-GB voices) and faster-whisper-small for CPU INT8 recognition. Model weights and pronunciation dictionaries are provisioned during installer build, not downloaded at first run. Audio is processed locally, with no hosted speech fallback. See [docs/LOCAL_RUNTIME_AND_VOICE.md](docs/LOCAL_RUNTIME_AND_VOICE.md) for exact configuration and remaining device tests.
