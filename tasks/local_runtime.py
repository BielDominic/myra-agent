"""Local runtime, Docker and offline voice endpoints for MYRA.

All Docker operations are restricted to a fixed compose project and allowlisted services.
No arbitrary shell, image, port, mount or container command is accepted from the UI.
"""
from __future__ import annotations

import json
import os
import re
import asyncio
import socket
import shutil
import subprocess
import secrets
import tempfile
import threading
import urllib.request
import urllib.error
from urllib.parse import urlparse
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.concurrency import run_in_threadpool
from starlette.background import BackgroundTask
from pydantic import BaseModel, Field

router = APIRouter(tags=["local-runtime"])
ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "docker-compose.yml"
CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MYRA"
CONFIG_FILE = CONFIG_DIR / "runtime_config.json"
DOCKER_ENV_FILE = CONFIG_DIR / "docker-compose.env"
VOICE_DIR = CONFIG_DIR / "voice"
VOICE_ASSET_ROOT = Path(os.environ.get("MYRA_VOICE_ASSET_ROOT", str(VOICE_DIR)))
ALLOWED_SERVICES = {"ollama", "searxng"}
ALLOWED_ACTIONS = {"start", "stop", "restart"}
_lock = threading.Lock()
_voice_model_lock = threading.Lock()
_whisper_model = None
_whisper_model_path = None
_kokoro_lock = threading.RLock()
_kokoro_engines: dict[str, tuple[float, object]] = {}
KOKORO_CACHE_DIR = VOICE_ASSET_ROOT / "kokoro-assets"
WHISPER_MODEL_DIR = VOICE_ASSET_ROOT / "whisper-small"

KOKORO_VOICES = {
    "pt-br": {"pf_dora", "pm_alex", "pm_santa"},
    "en-us": {"af_sarah", "af_heart", "af_bella", "af_nova", "am_michael", "am_adam", "am_onyx"},
    "en-gb": {"bf_emma", "bf_alice", "bm_daniel", "bm_george"},
}


def _detect_speech_language(text: str) -> str:
    value = str(text or "").lower()
    has_pt_marks = bool(re.search(r"[áàâãéêíóôõúç]", value))
    pt = len(re.findall(r"\b(ola|olá|oi|obrigado|obrigada|voce|você|nao|não|tambem|também|esta|está|sao|são|acao|ação|porque|entao|então|isso|essa|esse|sobre|aqui|agora|vamos|fazer|tenho|tem|para|com|uma|mais|como|pode|posso|seu|sua|pela|pelo|das|dos)\b", value))
    en = len(re.findall(r"\b(the|and|you|your|how|what|when|where|why|can|could|would|should|will|have|has|with|from|this|that|there|here|hello|thanks|please|because|about|into|for|are|was|were|is|not|yes|no|today|tomorrow)\b", value))
    return "pt-br" if has_pt_marks or pt >= en else "en-us"


def _kokoro_assets_ready() -> bool:
    if not KOKORO_CACHE_DIR.is_dir():
        return False
    try:
        models = list(KOKORO_CACHE_DIR.glob("installs/kokoro/**/kokoro-v1.0.onnx"))
        voices = list(KOKORO_CACHE_DIR.glob("installs/kokoro/**/voices-v1.0.npz"))
        catalog = KOKORO_CACHE_DIR / "catalogs" / "kokoro.json"
        return bool(models and voices and catalog.is_file() and catalog.stat().st_size > 10_000
                    and models[0].stat().st_size > 100_000_000 and voices[0].stat().st_size > 1_000_000)
    except OSError:
        return False


def _get_kokoro_engine(language: str, voice: str, speed: float):
    engine_key = "en" if language.startswith("en-") else "pt-br"
    engine_language = "en-us" if engine_key == "en" else "pt-br"
    with _kokoro_lock:
        cached = _kokoro_engines.get(engine_key)
        if cached and cached[0] == speed:
            return cached[1]
        if cached:
            try:
                cached[1].close()
            except Exception:
                pass
        try:
            from pykokoro import GenerationConfig, KokoroSynthesizer, SynthesisConfig, TokenizerConfig
        except Exception as exc:
            raise HTTPException(503, f"Kokoro TTS is not installed: {exc}") from exc
        os.environ.setdefault("LEXPHON_DATA_HOME", str(VOICE_ASSET_ROOT / "lexphon"))
        tokenizer = TokenizerConfig(
            fallback="none", use_spacy=False,
            lexicons=("gold",) if language.startswith("en-") else (),
            lexicon_data_policy="installed-only",
        )
        config = SynthesisConfig(
            voice=voice, generation=GenerationConfig(lang=engine_language, speed=speed),
            cache_dir=KOKORO_CACHE_DIR, provider="cpu", tokenizer_config=tokenizer,
            long_text_split="sentence", long_text_use_spacy=False,
        )
        try:
            engine = KokoroSynthesizer(config)
        except Exception as exc:
            raise HTTPException(503, f"Could not initialize the local Kokoro voice engine: {exc}") from exc
        _kokoro_engines[engine_key] = (speed, engine)
        return engine


def _load_config() -> dict:
    defaults = {
        "mode": "native",
        "offline_first": True,
        "servers": {
            "ollama": {"url": "http://127.0.0.1:11434", "enabled": True},
            "myra": {"url": "http://127.0.0.1:8000", "enabled": True},
            "comfyui": {"url": "http://127.0.0.1:8188", "enabled": False},
            "searxng": {"url": "http://127.0.0.1:8080", "enabled": False},
            "whisper": {"url": "local://faster-whisper", "enabled": True},
            "kokoro": {"url": "local://kokoro", "enabled": True},
        },
        "channels": {
            "desktop": True, "telegram": False, "browser": True,
            "remote_api": False, "voice": True,
        },
        "providers": {"external_enabled": False, "active": "local", "items": []},
        "voice": {
            "stt_engine": "faster-whisper", "stt_model_path": str(WHISPER_MODEL_DIR),
            "stt_language": "auto", "tts_engine": "kokoro", "tts_language": "auto",
            "pt_voice": "pf_dora", "en_voice": "af_sarah", "en_gb_voice": "bf_emma",
            "tts_speed": 1.0, "piper_executable": "", "piper_model_path": "",
            "auto_speak": False, "auto_send": True, "continuous": False, "wake_word": False,
        },
    }
    try:
        saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if isinstance(saved, dict):
            for key, value in saved.items():
                if isinstance(value, dict) and isinstance(defaults.get(key), dict):
                    for subkey, subvalue in value.items():
                        if isinstance(subvalue, dict) and isinstance(defaults[key].get(subkey), dict):
                            defaults[key][subkey].update(subvalue)
                        else:
                            defaults[key][subkey] = subvalue
                else:
                    defaults[key] = value
    except (OSError, ValueError):
        pass
    servers = defaults.get("servers", {})
    servers.pop("piper", None)
    servers.setdefault("kokoro", {"url": "local://kokoro", "enabled": True})
    voice = defaults.get("voice", {})
    voice.pop("piper_executable", None)
    voice.pop("piper_model_path", None)
    if not str(voice.get("stt_model_path") or "").strip() and WHISPER_MODEL_DIR.is_dir():
        voice["stt_model_path"] = str(WHISPER_MODEL_DIR)
    return defaults


def _save_config(data: dict) -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, CONFIG_FILE)
    return data


def _ensure_compose_env() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not DOCKER_ENV_FILE.exists():
        DOCKER_ENV_FILE.write_text("MYRA_SEARXNG_SECRET=" + secrets.token_urlsafe(48) + "\n", encoding="utf-8")


def _docker(*args: str, timeout: int = 20) -> subprocess.CompletedProcess:
    _ensure_compose_env()
    exe = shutil.which("docker")
    if not exe:
        raise HTTPException(503, "Docker CLI não encontrado. Instale/ative o Docker Desktop ou Engine.")
    if not COMPOSE_FILE.is_file():
        raise HTTPException(503, "docker-compose.yml da MYRA não encontrado.")
    cmd = [exe, "compose", "--env-file", str(DOCKER_ENV_FILE), "-f", str(COMPOSE_FILE), "--project-name", "myra-local", *args]
    try:
        return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                              timeout=timeout, check=False, shell=False)
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Docker não respondeu dentro do limite de tempo.")


def _docker_status() -> dict:
    if not shutil.which("docker"):
        return {"installed": False, "available": False, "error": "Docker CLI não encontrado", "containers": []}
    try:
        info = subprocess.run([shutil.which("docker"), "info", "--format", "{{.ServerVersion}}"],
                              capture_output=True, text=True, timeout=5, check=False, shell=False)
        if info.returncode:
            return {"installed": True, "available": False, "error": (info.stderr or info.stdout).strip()[:500], "containers": []}
        ps = _docker("ps", "--all", "--format", "json")
        containers = []
        if ps.returncode == 0:
            for line in ps.stdout.splitlines():
                try:
                    item = json.loads(line)
                    if str(item.get("Names", "")).startswith("myra-local-"):
                        containers.append({
                            "name": item.get("Names"), "image": item.get("Image"),
                            "state": item.get("State"), "status": item.get("Status"),
                            "ports": item.get("Ports", ""),
                        })
                except ValueError:
                    continue
        return {"installed": True, "available": True, "version": info.stdout.strip(), "containers": containers}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"installed": True, "available": False, "error": str(exc)[:500], "containers": []}


class RuntimeConfigUpdate(BaseModel):
    config: dict = Field(..., description="Runtime configuration; secrets are not accepted here.")


@router.get("/runtime/config")
def runtime_config():
    return _load_config()


@router.put("/runtime/config")
def update_runtime_config(body: RuntimeConfigUpdate):
    current = _load_config()
    incoming = body.config
    for section in ("mode", "offline_first", "servers", "channels", "providers", "voice"):
        if section not in incoming:
            continue
        value = incoming[section]
        if section in ("servers", "channels", "providers", "voice"):
            if not isinstance(value, dict):
                raise HTTPException(422, f"Invalid configuration section: {section}")
            existing = current.get(section, {})
            for key, child in value.items():
                if isinstance(child, dict) and isinstance(existing.get(key), dict):
                    existing[key].update(child)
                else:
                    existing[key] = child
            current[section] = existing
        else:
            current[section] = value
    if current.get("mode") not in ("native", "docker", "hybrid"):
        raise HTTPException(422, "mode must be native, docker or hybrid")
    current["offline_first"] = bool(current.get("offline_first", True))
    allowed_servers = {"myra", "ollama", "comfyui", "searxng", "whisper", "kokoro"}
    allowed_channels = {"desktop", "telegram", "browser", "remote_api", "voice"}
    if set(current.get("servers", {})) - allowed_servers:
        raise HTTPException(422, "Unknown server name")
    if set(current.get("channels", {})) - allowed_channels:
        raise HTTPException(422, "Unknown channel name")
    for name, server in current.get("servers", {}).items():
        if not isinstance(server, dict):
            raise HTTPException(422, f"Invalid server configuration: {name}")
        url = str(server.get("url", ""))
        if url.startswith("local://"):
            continue
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in ("http", "https") or host not in ("127.0.0.1", "localhost", "::1"):
            raise HTTPException(422, f"Local server must use loopback or local://: {name}")
    forbidden = {"api_key", "apikey", "token", "secret", "password", "authorization"}
    def reject_secrets(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if str(key).lower() in forbidden:
                    raise HTTPException(422, "Credentials cannot be stored in runtime settings; use a secure vault.")
                reject_secrets(child)
        elif isinstance(value, list):
            for child in value:
                reject_secrets(child)
    reject_secrets(current.get("providers", {}))
    voice = current.get("voice", {})
    if voice.get("tts_language", "auto") not in ("auto", "pt-br", "en-us", "en-gb"):
        raise HTTPException(422, "Unsupported TTS language")
    for key, language in (("pt_voice", "pt-br"), ("en_voice", "en-us"), ("en_gb_voice", "en-gb")):
        if voice.get(key) and voice[key] not in KOKORO_VOICES[language]:
            raise HTTPException(422, f"Unsupported Kokoro voice for {language}")
    try:
        speed = float(voice.get("tts_speed", 1.0))
    except (TypeError, ValueError):
        raise HTTPException(422, "Invalid TTS speed")
    if not 0.85 <= speed <= 1.15:
        raise HTTPException(422, "TTS speed must be between 0.85 and 1.15")
    voice["tts_speed"] = speed
    return _save_config(current)


@router.get("/runtime/status")
def runtime_status():
    cfg = _load_config()
    docker = _docker_status()
    return {
        "mode": cfg.get("mode"), "offline_first": cfg.get("offline_first"),
        "docker": docker, "servers": cfg.get("servers", {}),
        "channels": cfg.get("channels", {}),
        "external_providers_enabled": bool(cfg.get("providers", {}).get("external_enabled")),
    }




@router.post("/runtime/probe/{server}")
def runtime_probe(server: str):
    cfg = _load_config()
    if server not in {"myra", "ollama", "comfyui", "searxng", "whisper", "kokoro"}:
        raise HTTPException(404, "Servidor n?o permitido.")
    if server in {"whisper", "kokoro"}:
        status = voice_status()
        engine = status["stt"] if server == "whisper" else status["tts"]
        ready = bool(engine.get("package_installed") and engine.get("model_configured"))
        return {"server": server, "reachable": ready, "detail": "Motor local pronto." if ready else "Pacote ou modelo local ausente.", "status": engine}
    item = cfg.get("servers", {}).get(server, {})
    url = str(item.get("url", "")).rstrip("/")
    if url.startswith("local://"):
        return {"server": server, "reachable": False, "detail": "Motor local configuravel; verifique o estado em /voice/status."}
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or (parsed.hostname or "").lower() not in ("127.0.0.1", "localhost", "::1"):
        raise HTTPException(422, "A verifica??o aceita apenas endpoints HTTP locais (loopback).")
    paths = {"myra": "/", "ollama": "/api/tags", "comfyui": "/system_stats", "searxng": "/"}
    target = url + paths[server]
    try:
        req = urllib.request.Request(target, headers={"User-Agent": "MYRA-local-health/1.0"})
        with urllib.request.urlopen(req, timeout=3) as response:
            return {"server": server, "reachable": 200 <= response.status < 400, "status_code": response.status, "url": url}
    except urllib.error.HTTPError as exc:
        return {"server": server, "reachable": exc.code < 500, "status_code": exc.code, "url": url, "detail": "Servidor respondeu com HTTP " + str(exc.code)}
    except Exception as exc:
        return {"server": server, "reachable": False, "url": url, "detail": str(exc)[:300]}


@router.get("/runtime/containers")
def runtime_containers():
    return _docker_status()


@router.post("/runtime/service/{service}/{action}")
def runtime_service_action(service: str, action: Literal["start", "stop", "restart"]):
    if service not in ALLOWED_SERVICES or action not in ALLOWED_ACTIONS:
        raise HTTPException(404, "Serviço ou ação não permitidos.")
    with _lock:
        if action == "start":
            port = {"ollama": 11434, "searxng": 8080}[service]
            docker_items = _docker_status().get("containers", [])
            running = any(item.get("name") == f"myra-local-{service}" and item.get("state") == "running" for item in docker_items)
            if not running:
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.35):
                        raise HTTPException(409, f"A porta {port} j? est? em uso. Pare o servi?o nativo antes de iniciar o container; a MYRA n?o encerrar? processos do host automaticamente.")
                except OSError:
                    pass
            result = _docker("up", "-d", service, timeout=180)
        else:
            result = _docker(action, service, timeout=90)
    if result.returncode:
        raise HTTPException(502, (result.stderr or result.stdout or "Falha no Docker Compose")[-2000:])
    return {"ok": True, "service": service, "action": action, "output": result.stdout[-2000:], "docker": _docker_status()}


@router.get("/voice/status")
def voice_status():
    cfg = _load_config().get("voice", {})
    model_value = str(cfg.get("stt_model_path") or "").strip()
    model = Path(model_value) if model_value else None
    try:
        import faster_whisper  # noqa: F401
        whisper_package = True
    except Exception:
        whisper_package = False
    try:
        import pykokoro  # noqa: F401
        kokoro_package = True
    except Exception:
        kokoro_package = False
    assets_ready = _kokoro_assets_ready()
    return {
        "stt": {"engine": "faster-whisper", "model": "small", "compute_type": "int8-cpu", "package_installed": whisper_package,
                "model_configured": bool(model and model.exists()),
                "model_path": str(model) if model and model.exists() else None},
        "tts": {"engine": "kokoro", "package_installed": kokoro_package,
                "model_configured": assets_ready, "cache_path": str(KOKORO_CACHE_DIR) if assets_ready else None,
                "voices": {key: sorted(value) for key, value in KOKORO_VOICES.items()},
                "selected": {"pt-br": cfg.get("pt_voice", "pf_dora"), "en-us": cfg.get("en_voice", "af_sarah"),
                             "en-gb": cfg.get("en_gb_voice", "bf_emma")}},
        "auto_speak": bool(cfg.get("auto_speak")), "wake_word": bool(cfg.get("wake_word")),
        "privacy": "local-only; Kokoro TTS and Whisper STT process audio/text on this device; no hosted speech API fallback",
    }


@router.post("/voice/transcribe")
async def voice_transcribe(request: Request):
    cfg = _load_config().get("voice", {})
    audio = await request.body()
    if not audio or len(audio) > 25 * 1024 * 1024:
        raise HTTPException(413, "Áudio vazio ou maior que 25 MB.")
    model_value = str(cfg.get("stt_model_path") or "").strip()
    model_path = Path(model_value) if model_value else None
    if not model_path or not model_path.exists():
        raise HTTPException(503, "Local Whisper model is not configured. Select an existing on-disk model; automatic downloads are disabled.")
    try:
        from faster_whisper import WhisperModel
    except Exception:
        raise HTTPException(503, "faster-whisper não está instalado. A transcrição local permanece desativada até instalar a dependência.")
    suffix = ".webm" if "webm" in request.headers.get("content-type", "") else ".wav"
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=suffix, dir=VOICE_DIR, delete=False) as tmp:
        tmp.write(audio)
        audio_path = Path(tmp.name)
    try:
        def transcribe_local():
            global _whisper_model, _whisper_model_path
            with _voice_model_lock:
                if _whisper_model is None or _whisper_model_path != str(model_path):
                    _whisper_model = WhisperModel(str(model_path), device="cpu", compute_type="int8", local_files_only=True)
                    _whisper_model_path = str(model_path)
                model = _whisper_model
            selected_language = str(cfg.get("stt_language") or "auto").lower()
            language = None if selected_language in ("", "auto") else selected_language
            segments, info = model.transcribe(str(audio_path), language=language, vad_filter=True)
            transcript = " ".join(segment.text.strip() for segment in segments).strip()
            return {"text": transcript, "language": info.language, "duration": info.duration, "engine": "faster-whisper-local"}
        return await run_in_threadpool(transcribe_local)
    finally:
        audio_path.unlink(missing_ok=True)


@router.post("/voice/speak")
async def voice_speak(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(422, "Expected a JSON request.")
    text = str(payload.get("text", "")).strip()
    if not text or len(text) > 12000:
        raise HTTPException(422, "Texto vazio ou excede 12.000 caracteres.")
    cfg = _load_config().get("voice", {})
    language = str(payload.get("language") or cfg.get("tts_language") or "pt-br").lower()
    if language == "auto": language = _detect_speech_language(text)
    if language == "pt": language = "pt-br"
    if language in ("en", "en-us"): language = "en-us"
    if language in ("en-gb", "en_uk"): language = "en-gb"
    if language not in KOKORO_VOICES:
        raise HTTPException(422, "Unsupported local speech language. Use pt-br, en-us or en-gb.")
    default_voice = cfg.get("pt_voice", "pf_dora") if language == "pt-br" else cfg.get("en_gb_voice", "bf_emma") if language == "en-gb" else cfg.get("en_voice", "af_sarah")
    voice = str(payload.get("voice") or default_voice)
    if voice not in KOKORO_VOICES[language]:
        raise HTTPException(422, "The selected Kokoro voice is not compatible with the requested language.")
    try:
        speed = float(cfg.get("tts_speed", 1.0))
    except (TypeError, ValueError):
        speed = 1.0
    speed = max(0.85, min(1.15, speed))
    if not _kokoro_assets_ready():
        raise HTTPException(503, "Kokoro voice assets are missing. Re-run the MYRA installer to restore the bundled offline voice pack.")
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    fd, output_name = tempfile.mkstemp(suffix=".wav", dir=VOICE_DIR)
    os.close(fd)
    output = Path(output_name)
    try:
        def synthesize():
            with _kokoro_lock:
                engine = _get_kokoro_engine(language, voice, speed)
                rendered = engine.synthesize_text(text, language=language, voice=voice)
                rendered.save_wav(output)
            if not output.is_file() or output.stat().st_size < 1024:
                raise RuntimeError("Kokoro returned an empty audio file.")
        await run_in_threadpool(synthesize)
        return FileResponse(output, media_type="audio/wav", filename="myra-response.wav",
                            background=BackgroundTask(output.unlink, missing_ok=True))
    except HTTPException:
        output.unlink(missing_ok=True)
        raise
    except Exception as exc:
        output.unlink(missing_ok=True)
        raise HTTPException(502, f"Local Kokoro synthesis failed: {str(exc)[:800]}") from exc
