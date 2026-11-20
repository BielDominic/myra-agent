# MYRA ? Local Runtime and Voice

Updated: 2026-11-20

## Mandatory offline voice stack

MYRA now ships both speech directions in the Windows installer:

- **Speech output (TTS):** Kokoro v1.0 ONNX through `pykokoro==0.10.13` and ONNX Runtime CPU. Bundled profiles include Brazilian Portuguese (`pf_dora`, `pm_alex`, `pm_santa`), US English (`af_sarah`, `af_heart`, `af_bella`, `af_nova`, `am_michael`, `am_adam`, `am_onyx`) and UK English (`bf_emma`, `bf_alice`, `bm_daniel`, `bm_george`). The desktop selects a language automatically from the assistant reply or uses an explicit Settings override. Voice choice and speaking speed are configurable.
- **Speech input (STT):** `faster-whisper==1.2.1` with the multilingual `Systran/faster-whisper-small` model, CPU INT8. Recognition can auto-detect Portuguese/English or use an explicit language override.
- **Offline pronunciation:** en-US and en-GB Lexphon `gold` dictionaries are bundled. Runtime G2P uses `installed-only` and disables fallback, so it does not fetch dictionaries or invoke hosted speech services.
- **Privacy:** audio capture is sent only to the loopback FastAPI process. No hosted speech API fallback is used.

The installer build downloads and validates the Kokoro model/voice pack, Lexphon dictionaries and Whisper model into `installer/backend/voice-assets`. The installer requires both model directories and refuses to complete if either is missing. Python wheels for Kokoro, ONNX Runtime, faster-whisper, CTranslate2 and compatible PyAV are pinned in the mandatory offline core wheelhouse. The installed app does not download speech models on first run.

## Voice interaction

- Microphone capture uses `MediaRecorder` in the Tauri WebView.
- `/voice/transcribe` accepts local audio, loads the packaged Whisper model with `local_files_only=True`, and runs CPU INT8.
- `/voice/speak` synthesizes WAV audio with Kokoro locally.
- A voice-submitted command automatically receives a spoken reply even when global auto-speak is disabled.
- Auto-speak, auto-send, continuous conversation, language, voice and speed are configurable.
- Pressing the microphone interrupts current playback before recording again.
- If Kokoro cannot be loaded, the only fallback is the locally installed Windows/WebView speech synthesis voice; there is no cloud fallback.

## Validation completed

- Fresh Python 3.14 virtual environment installed the core wheelhouse with `--no-index`; `pip check` and imports passed.
- Kokoro WAV generation passed for pt-BR, en-US and en-GB voice profiles.
- Local TTS -> Whisper STT round-trip passed for Portuguese and English test phrases.
- Installer payload includes the Kokoro ONNX model/voice pack, Whisper small model and pronunciation dictionaries.

## Remaining before voice is production-ready

1. Validate microphone permissions, real capture and playback in the packaged Tauri/WebView on a physical audio device.
2. Test clean install, first launch with internet disabled, Windows restart and installer upgrade without downloading models.
3. Add VAD/silence segmentation, acoustic echo handling, audio-device selection, volume and more robust barge-in.
4. Add an optional local wake-word engine with false-activation/privacy tests; wake-word listening remains disabled.

## Local runtime and Docker

The native desktop includes a Servers & Docker view backed by `tasks/local_runtime.py`. It manages a fixed Compose project for local Ollama and optional SearXNG, reports container status, probes loopback endpoints, and stores server/channel preferences under the current Windows user's MYRA data directory. Docker actions are allowlisted and never accept arbitrary commands, images, mounts or ports. The Docker environment secret is generated per user outside the repository. Starting a service is explicit.

Docker is an optional service layer, not a replacement for the host agent. The Tauri desktop, FastAPI backend, browser bridge and Windows UI Automation remain on the host because they need access to the interactive Windows session. Full backend containerization remains a separate roadmap item.
