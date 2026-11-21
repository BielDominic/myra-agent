# MYRA Plugin Architecture

## Goal
Provide a first-party MYRA plugin library with a local catalogue, bundled installable packages, local ZIP import, installed-package management and chat integration. The library does not embed or depend on the Open WebUI community catalogue. Current installable packages are declarative Skills/Prompts; executable third-party Tools require the isolated worker and explicit capability grants described below.

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
1. Discover bundled first-party packages in the MYRA catalogue or import a local ZIP.
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
- Plugin package validation and runtime isolation are maintained inside MYRA; third-party executable code must never be imported into the FastAPI process.
- Continue: https://github.com/continuedev/continue
- Aider: https://github.com/Aider-AI/aider
- OpenHands: https://github.com/All-Hands-AI/OpenHands
- whisper.cpp: https://github.com/ggml-org/whisper.cpp
- Piper: https://github.com/rhasspy/piper

## Current local API (stage A — declarative intake)
- `GET /plugins/catalog`: return the first-party MYRA catalogue joined with installed/enabled state.
- `GET /plugins/catalog/{plugin_id}/package`: build and return a bundled MYRA Skill/Prompt ZIP for local installation.
- `GET /plugins`: list installed packages and their state.
- `POST /plugins/{plugin_id}/enable` and `/disable`: change declarative library state; activation does not grant tools or execute code.
- `POST /plugins/validate`: validate a raw ZIP body (`Content-Type: application/zip`) without installing it.
- `POST /plugins/install`: validate and install a raw ZIP body. The registry records SHA-256 and starts with `enabled=false`.
- `DELETE /plugins/{plugin_id}`: remove all installed versions only while every version is disabled.
- Current accepted package types are `skill` and `prompt`, with Markdown/text entry points. `myra.plugin.json`, `README.md`, and a licence file are required. No script, Python, JavaScript, native binary, requested permission, or capability is accepted.
- Upload is streamed with a 20 MB compressed limit; extraction is bounded to 50 MB / 500 files, rejects traversal, backslashes, symlinks and duplicate paths, and stages files before an atomic directory move.
- The native desktop plugin view loads the MYRA catalogue, filters/searches entries, installs bundled packages after validation/confirmation, imports local ZIPs, lists installed packages, enables/disables declarative content and removes disabled packages. No community catalogue or Git URL source is embedded.
- Enabled Skill/Prompt entry points are loaded into normal local chat as bounded (32 KiB total), explicitly untrusted reference context. This does not expose tool capabilities and does not execute package code.

## Delivery stages
- A (declarative lifecycle implemented): first-party MYRA catalogue, bundled installable Skill packages, ZIP validator, local registry, safe install/enable/disable/remove and bounded active Skill/Prompt context in chat. Native local ZIP import/list/manage UI is wired.
- B: native Tool adapters and explicit capability grants.
- C: restricted worker runtime, MCP connectors and per-capability permissions.
- D: updates, rollback, audit and signed catalogue metadata.
