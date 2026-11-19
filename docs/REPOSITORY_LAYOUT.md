# Repository layout and cleanup plan

## Active source directories

- src/: MYRA native desktop workspace (HTML, CSS and JavaScript).
- src-tauri/: Tauri desktop shell, native commands and Windows bundle configuration.
- widget/: legacy web widget assets retained for compatibility.
- widget-tauri/: standalone widget/tray implementation.
- agent.py: FastAPI application and API routes.
- computer/: desktop, browser and vision automation.
- tasks/: planner, autonomy, persistence, Telegram and task orchestration.
- tools/: native tool adapters.
- browser-extension/: Chrome MV3 bridge.
- llm-eyes/: local visual inference service.
- installer/backend/: backend payload copied into Windows releases.
- tests/: automated tests.
- docs/: architecture, design contracts, phase notes, context history and implementation notes.
- plugins/: plugin manifest/catalogue and future registry.
- archive/backups/: local-only dated source and roadmap backups preserved for recovery; excluded from Git.
- scripts/dev/legacy-patches/: one-off historical patch scripts; not part of runtime.
- docs/phases/: historical phase specifications and validation notes.
- docs/context-history/: previous handoff/context snapshots.
- docs/project-notes/: development notes and scratch records.

## Documentation

- README.md: product overview, install links and developer entry point.
- INSTALL_WINDOWS.md: Windows installation steps.
- ROADMAP.md: bilingual feature status and planned work.
- ARCHITECTURE.md: system architecture.
- docs/PLUGIN_ARCHITECTURE.md: plugin lifecycle, package contract and security.
- docs/REPOSITORY_LAYOUT.md: this file.

## Cleanup rules

1. Do not move files that are referenced by Tauri resource paths, Python imports, PowerShell scripts, tests, or installer manifests until the references are mapped.
2. Move dated one-off backups into archive/backups only after confirming they are not runtime inputs.
3. Move scratch scripts into scripts/dev or archive/experiments after identifying any scheduled or documented invocation.
4. Keep runtime logs, user data, browser profiles, .env, local models and generated build output out of Git.
5. Keep installer/backend synchronized with the tested root backend using a reproducible packaging script; do not edit release copies by hand.
6. Every move must preserve history where possible and be followed by import, test, build and installer checks.
