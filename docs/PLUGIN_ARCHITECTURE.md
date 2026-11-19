# MYRA Plugin Architecture

## Goal
Provide an Open-WebUI-style plugin library in MYRA plus a free-form source field for Git URLs, ZIP packages, or local folders. Catalogue entries are references, not endorsements. Untrusted code is never silently executed.

## Plugin classes
| Type | Purpose | Surface |
|---|---|---|
| Tool | Callable capability for the agent | Chat tool picker |
| Skill | Reusable workflow and instructions | Prompt-bar toggles |
| Prompt | Saved task templates | Prompt library |
| Filter | Context enrichment and response validation | Pipeline settings |
| Provider | LLM, STT, TTS and embedding adapters | Model/voice settings |
| MCP server | External MCP tools | Integrations |
| UI extension | Constrained panel, message action or view | Workspace |

## Package contract
Every package must include `myra.plugin.json`, README, licence, source and optional tests. Manifest fields: stable ID, semantic version, name, description, author, homepage, repository, entry point, type, minimum MYRA version, dependencies, capabilities, permissions and settings schema.

Registry records source URL, pinned commit/tag, SHA-256, install/enabled state, granted permissions, validation time and audit events.

## Lifecycle
1. Discover in the catalogue or enter a Git URL / ZIP / folder.
2. Inspect manifest, README, author, licence, version, dependencies and permissions.
3. Validate manifest, package size, paths, symlinks, duplicate IDs and supported version.
4. Review source and requested capabilities.
5. Install to the user plugin directory; pin exact version and hash. Never run install scripts automatically.
6. Enable only through a restricted worker with explicit permissions, timeouts and structured JSON I/O.
7. Update, rollback or remove with diffs, permission-change review and audit records.

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

## Delivery stages
- A: catalogue, free-form source field, manifest validator, local registry, disabled-by-default packages.
- B: declarative Skills/Prompts and native Tool adapters.
- C: restricted worker runtime, MCP connectors and per-capability permissions.
- D: updates, rollback, audit and signed catalogue metadata.
