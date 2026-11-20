from __future__ import annotations

import os
import tempfile
import hashlib
import json
from pathlib import Path

from pykokoro import GenerationConfig, KokoroSynthesizer, SynthesisConfig, TokenizerConfig
from faster_whisper import WhisperModel
from huggingface_hub import snapshot_download

CACHE = Path(os.environ["MYRA_KOKORO_CACHE_DIR"])
CACHE.mkdir(parents=True, exist_ok=True)
WHISPER = Path(os.environ["MYRA_WHISPER_MODEL_DIR"])
WHISPER.mkdir(parents=True, exist_ok=True)

samples = (
    ("pt-br", "pf_dora", "Oi! Eu sou a Myra. Como posso ajudar voc\u00ea hoje?"),
    ("en-us", "af_sarah", "Hello! I am Myra. How can I help you today?"),
    ("en-gb", "bf_emma", "Hello! I am Myra. How can I help you today?"),
)
for language, voice, phrase in samples:
    tokenizer = TokenizerConfig(
        fallback="none", use_spacy=False,
        lexicons=("gold",) if language.startswith("en-") else (),
        lexicon_data_policy="installed-only",
    )
    config = SynthesisConfig(
        voice=voice,
        generation=GenerationConfig(lang=language, speed=1.0),
        cache_dir=CACHE,
        provider="cpu",
        tokenizer_config=tokenizer,
        long_text_split="sentence",
        long_text_use_spacy=False,
    )
    with KokoroSynthesizer(config) as synthesizer:
        rendered = synthesizer.synthesize_text(phrase, language=language, voice=voice)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir=CACHE) as handle:
            sample_path = Path(handle.name)
        try:
            rendered.save_wav(sample_path)
            if not sample_path.is_file() or sample_path.stat().st_size < 1024:
                raise RuntimeError(f"Kokoro {language} voice warm-up produced no audio")
            print(f"Validated {language}/{voice}: {sample_path.stat().st_size:,} bytes", flush=True)
        finally:
            sample_path.unlink(missing_ok=True)

models = list(CACHE.glob("installs/kokoro/**/kokoro-v1.0.onnx"))
voices = list(CACHE.glob("installs/kokoro/**/voices-v1.0.npz"))
if not models or not voices:
    raise RuntimeError("Kokoro v1.0 model/voice assets were not provisioned")
if models[0].stat().st_size < 100_000_000 or voices[0].stat().st_size < 1_000_000:
    raise RuntimeError("Kokoro voice asset size validation failed")
print(f"Kokoro offline assets ready: model={models[0].stat().st_size:,} voices={voices[0].stat().st_size:,}", flush=True)

# Bundle the multilingual CPU-INT8 Whisper small model so offline voice commands work immediately.
snapshot_download(
    repo_id="Systran/faster-whisper-small",
    revision="536b0662742c02347bc0e980a01041f333bce120",
    local_dir=str(WHISPER),
    allow_patterns=["config.json", "model.bin", "tokenizer.json", "vocabulary.txt"],
)
model = WhisperModel(str(WHISPER), device="cpu", compute_type="int8", local_files_only=True)
del model
required = ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt")
if any(not (WHISPER / name).is_file() for name in required):
    raise RuntimeError("Whisper small offline model is incomplete")
if (WHISPER / "model.bin").stat().st_size < 400_000_000:
    raise RuntimeError("Whisper small model size validation failed")
print(f"Whisper small offline model ready: {(WHISPER / 'model.bin').stat().st_size:,} bytes", flush=True)

# Integrity manifest for the offline model payload.
def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

kokoro_model = models[0]
kokoro_voices = voices[0]
lexicons = sorted(WHISPER.parent.rglob("*.g2lex"))
manifest = {
    "schema": "myra-offline-voice-v1",
    "kokoro": {"model": "Kokoro-82M-v1.0-ONNX", "engine": "pykokoro==0.10.13", "onnxruntime": "1.31.0",
               "model_file": "kokoro-assets/" + str(kokoro_model.relative_to(CACHE)).replace("\\", "/"),
               "model_sha256": sha256(kokoro_model),
               "voices_file": "kokoro-assets/" + str(kokoro_voices.relative_to(CACHE)).replace("\\", "/"),
               "voices_sha256": sha256(kokoro_voices),
               "profiles": ["pt-br:pf_dora", "pt-br:pm_alex", "pt-br:pm_santa", "en-us:af_sarah", "en-us:af_heart", "en-us:af_bella", "en-us:af_nova", "en-us:am_michael", "en-us:am_adam", "en-us:am_onyx", "en-gb:bf_emma", "en-gb:bf_alice", "en-gb:bm_daniel", "en-gb:bm_george"]},
    "whisper": {"model": "Systran/faster-whisper-small", "revision": "536b0662742c02347bc0e980a01041f333bce120",
                "engine": "faster-whisper==1.2.1", "compute": "cpu-int8", "model_file": "whisper-small/model.bin",
                "model_sha256": sha256(WHISPER / "model.bin")},
    "lexphon": [{"file": str(path.relative_to(WHISPER.parent)).replace("\\", "/"), "sha256": sha256(path)} for path in lexicons],
}
(CACHE.parent / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print("Offline voice manifest written and SHA-256 hashes calculated.", flush=True)
