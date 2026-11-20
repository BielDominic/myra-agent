import json
import pytest
from fastapi import HTTPException
from tasks import local_runtime as runtime

def test_runtime_defaults_are_local_first():
    cfg = runtime._load_config()
    assert cfg["mode"] == "native"
    assert cfg["offline_first"] is True
    assert cfg["providers"]["external_enabled"] is False
    assert cfg["servers"]["ollama"]["url"].startswith("http://127.0.0.1")

def test_config_save_is_atomic_and_round_trips(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(runtime, "CONFIG_FILE", tmp_path / "runtime.json")
    cfg = runtime._load_config()
    cfg["voice"]["auto_send"] = True
    runtime._save_config(cfg)
    assert runtime._load_config()["voice"]["auto_send"] is True
    assert not (tmp_path / "runtime.tmp").exists()

def test_voice_status_does_not_treat_empty_model_path_as_current_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(runtime, "CONFIG_FILE", tmp_path / "missing.json")
    monkeypatch.setattr(runtime, "KOKORO_CACHE_DIR", tmp_path / "missing-kokoro")
    monkeypatch.setattr(runtime, "WHISPER_MODEL_DIR", tmp_path / "missing-whisper")
    result = runtime.voice_status()
    assert result["stt"]["model_configured"] is False
    assert result["stt"]["model_path"] is None
    assert result["tts"]["engine"] == "kokoro"
    assert result["tts"]["model_configured"] is False

def test_docker_service_allowlist_rejects_unknown_service():
    with pytest.raises(HTTPException) as exc:
        runtime.runtime_service_action("arbitrary-container", "start")
    assert exc.value.status_code == 404

def test_runtime_config_rejects_non_loopback_server(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(runtime, "CONFIG_FILE", tmp_path / "runtime.json")
    body = runtime.RuntimeConfigUpdate(config={"servers": {"ollama": {"url": "http://example.com:11434"}}})
    with pytest.raises(HTTPException) as exc:
        runtime.update_runtime_config(body)
    assert exc.value.status_code == 422


def test_runtime_config_rejects_api_secrets(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(runtime, "CONFIG_FILE", tmp_path / "runtime.json")
    body = runtime.RuntimeConfigUpdate(config={"providers": {"external_enabled": True, "items": [{"name": "hosted", "api_key": "do-not-store"}]}})
    with pytest.raises(HTTPException) as exc:
        runtime.update_runtime_config(body)
    assert exc.value.status_code == 422

def test_docker_start_refuses_to_clash_with_native_ollama(monkeypatch):
    class Connected:
        def __enter__(self): return self
        def __exit__(self, *args): return False
    monkeypatch.setattr(runtime, "_docker_status", lambda: {"containers": []})
    monkeypatch.setattr(runtime.socket, "create_connection", lambda *a, **k: Connected())
    with pytest.raises(HTTPException) as exc:
        runtime.runtime_service_action("ollama", "start")
    assert exc.value.status_code == 409

def test_runtime_probe_rejects_unknown_server():
    with pytest.raises(HTTPException) as exc:
        runtime.runtime_probe("external-host")
    assert exc.value.status_code == 404


def test_runtime_config_rejects_voice_for_wrong_language(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(runtime, "CONFIG_FILE", tmp_path / "runtime.json")
    body = runtime.RuntimeConfigUpdate(config={"voice": {"pt_voice": "af_sarah"}})
    with pytest.raises(HTTPException) as exc:
        runtime.update_runtime_config(body)
    assert exc.value.status_code == 422

def test_runtime_config_rejects_unsafe_tts_speed(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(runtime, "CONFIG_FILE", tmp_path / "runtime.json")
    body = runtime.RuntimeConfigUpdate(config={"voice": {"tts_speed": 2.0}})
    with pytest.raises(HTTPException) as exc:
        runtime.update_runtime_config(body)
    assert exc.value.status_code == 422

def test_runtime_config_accepts_kokoro_voice_preferences(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(runtime, "CONFIG_FILE", tmp_path / "runtime.json")
    body = runtime.RuntimeConfigUpdate(config={"voice": {"tts_engine": "kokoro", "tts_language": "auto", "pt_voice": "pm_alex", "en_voice": "am_michael", "en_gb_voice": "bm_daniel", "tts_speed": 0.95}})
    saved = runtime.update_runtime_config(body)
    assert saved["voice"]["pt_voice"] == "pm_alex"
    assert saved["voice"]["tts_speed"] == 0.95


def test_auto_speech_language_detection_for_portuguese_and_english():
    assert runtime._detect_speech_language("Oi, como voc? est?? Posso ajudar agora.") == "pt-br"
    assert runtime._detect_speech_language("Hello, how can I help you today?") == "en-us"


def test_runtime_probe_reports_local_whisper_and_kokoro_ready(monkeypatch):
    monkeypatch.setattr(runtime, "voice_status", lambda: {
        "stt": {"package_installed": True, "model_configured": True},
        "tts": {"package_installed": True, "model_configured": True},
    })
    assert runtime.runtime_probe("whisper")["reachable"] is True
    assert runtime.runtime_probe("kokoro")["reachable"] is True

def test_runtime_probe_reports_missing_local_voice_engine(monkeypatch):
    monkeypatch.setattr(runtime, "voice_status", lambda: {
        "stt": {"package_installed": True, "model_configured": False},
        "tts": {"package_installed": False, "model_configured": False},
    })
    assert runtime.runtime_probe("whisper")["reachable"] is False
    assert runtime.runtime_probe("kokoro")["reachable"] is False


def test_saved_piper_settings_migrate_to_kokoro(tmp_path, monkeypatch):
    config_file = tmp_path / "runtime.json"
    config_file.write_text(json.dumps({
        "servers": {"piper": {"url": "local://piper", "enabled": True}, "whisper": {"enabled": False}},
        "voice": {"piper_executable": "old-piper.exe", "piper_model_path": "old.onnx"},
    }), encoding="utf-8")
    monkeypatch.setattr(runtime, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(runtime, "CONFIG_FILE", config_file)
    monkeypatch.setattr(runtime, "WHISPER_MODEL_DIR", tmp_path / "missing-whisper")
    config = runtime._load_config()
    assert "piper" not in config["servers"]
    assert config["servers"]["kokoro"]["url"] == "local://kokoro"
    assert "piper_executable" not in config["voice"]
    assert "piper_model_path" not in config["voice"]
