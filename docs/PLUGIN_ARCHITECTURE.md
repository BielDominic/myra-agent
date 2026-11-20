# MYRA Plugin Architecture

## Goal
Provide a native MYRA library for reviewed capability references and declarative Skill/Prompt ZIP packages. Git URLs are queued for manual review; local-folder import and automatic repository fetching are not implemented. Catalogue entries are references, not endorsements.

## Plugin classes
| Type | Purpose | Surface |
|---|---|---|
| Tool | Callable capability for the agent | Planned; current tools remain built-in |
| Skill | Reusable workflow and instructions | Installed library; enabled text enters local chat context |
| Prompt | Saved task templates | Installed library; enabled text enters local chat context |
| Filter | Context enrichment and response validation | Pipeline settings |
| Provider | LLM, STT, TTS and embedding adapters | Model/voice settings |
| MCP server | External MCP tools | Integrations |
| UI extension | Constrained panel, message action or view | Workspace |

## Package contract
Current accepted packages must include `myra.plugin.json`, `README.md`, a licence file and a Markdown/text entry point. Required manifest fields are stable ID, semantic version, name, description, type (`skill` or `prompt`) and `entry_point`; capabilities and permissions must be empty. Author, homepage, repository, dependencies and settings schemas are future metadata.

The current registry records package identity/version, entry point, SHA-256, install/enabled state, install time and local path. Source pinning, granted permissions and audit events are planned.

## Lifecycle
1. Discover reviewed references in the catalogue, import a local ZIP, or add a Git URL to the manual-review queue.
2. Inspect the package manifest, README, licence, version and supported type.
3. Validate manifest, package size, paths, symlinks, duplicate IDs and supported version.
4. Review declarative text and its SHA-256. No package capabilities or permissions are accepted.
5. Install to the user plugin directory; record exact version and hash. Never run install scripts.
6. Enable declarative Skills/Prompts only as bounded, untrusted chat reference context. Executable plugins remain unsupported.
7. Disable and remove installed packages. Version update, rollback and audit records are future work.

## Security
- Never execute third-party Python inside the FastAPI process.
- Prefer declarative Skills and Prompts.
- Executable plugins run in a separate worker with minimal environment, allowlists, resource limits and timeouts.
- Network, filesystem, browser, shell, microphone and clipboard permissions are separate.
- Secrets belong in OS/backend credential storage, never manifests or browser localStorage.
- The model may request an action; the host permission layer decides whether it is allowed.
- Destructive actions and external side effects require confirmation.
- Only mark a package Installed after validation; only mark Enabled after a successful runtime load and recorded permission grant.

## Reference projects and docs
- Open WebUI extensibility: https://docs.openwebui.com/features/extensibility/
- Tools and Functions: https://docs.openwebui.com/features/extensibility/plugin/
- Tools reference: https://docs.openwebui.com/features/extensibility/plugin/tools/
- Security hardening: https://docs.openwebui.com/getting-started/advanced-topics/hardening/
- Continue: https://github.com/continuedev/continue
- Aider: https://github.com/Aider-AI/aider
- OpenHands: https://github.com/All-Hands-AI/OpenHands
- whisper.cpp: https://github.com/ggml-org/whisper.cpp
- Piper: https://github.com/rhasspy/piper

## Current local API (stage A — declarative intake)
- `GET /plugins/catalog`: return the reviewed local catalogue joined with installed/enabled state.
- `GET /plugins`: list installed packages and their state.
- `POST /plugins/{plugin_id}/enable` and `/disable`: change declarative library state; activation does not grant tools or execute code.
- `POST /plugins/validate`: validate a raw ZIP body (`Content-Type: application/zip`) without installing it.
- `POST /plugins/install`: validate and install a raw ZIP body. The registry records SHA-256 and starts with `enabled=false`.
- `DELETE /plugins/{plugin_id}`: remove all installed versions only while every version is disabled.
- Current accepted package types are `skill` and `prompt`, with Markdown/text entry points. `myra.plugin.json`, `README.md`, and a licence file are required. No script, Python, JavaScript, native binary, requested permission, or capability is accepted.
- Upload is streamed with a 20 MB compressed limit; extraction is bounded to 50 MB / 500 files, rejects traversal, backslashes, symlinks and duplicate paths, and stages files before an atomic directory move.
- The native desktop plugin view loads the real API catalogue, filters/searches entries, imports local ZIPs after validation/confirmation, lists installed packages, enables/disables declarative content and removes disabled packages. A Git URL is only queued for manual review; it is not fetched or installed.
- Enabled Skill/Prompt entry points are loaded into normal local chat as bounded (32 KiB total), explicitly untrusted reference context. This does not expose tool capabilities and does not execute package code.

## Delivery stages
- A (declarative lifecycle implemented): live catalogue, ZIP validator, local registry, safe install/enable/disable/remove and bounded active Skill/Prompt context in chat. Native local ZIP import/list/manage UI is wired; Git source fetching and manual review remain pending.
- B: native Tool adapters and explicit capability grants.
- C: restricted worker runtime, MCP connectors and per-capability permissions.
- D: updates, rollback, audit and signed catalogue metadata.
