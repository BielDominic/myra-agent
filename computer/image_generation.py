"""Local image generation through a user-installed ComfyUI server.

No hosted inference key, subscription, or per-image service fee is required.
A compatible open model checkpoint must be installed in ComfyUI by the user.
"""
from __future__ import annotations

import base64
import os
import secrets
import time
from pathlib import Path
from typing import Any

import requests

DEFAULT_URL = os.environ.get("MYRA_COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")


def status() -> dict:
    try:
        response = requests.get(f"{DEFAULT_URL}/system_stats", timeout=3)
        response.raise_for_status()
        data = response.json()
        checkpoints = requests.get(f"{DEFAULT_URL}/object_info/CheckpointLoaderSimple", timeout=5)
        checkpoints.raise_for_status()
        names = (checkpoints.json().get("CheckpointLoaderSimple", {}).get("input", {})
                 .get("required", {}).get("ckpt_name", [[]])[0])
        return {"status": "ok", "available": True, "url": DEFAULT_URL,
                "checkpoints": names if isinstance(names, list) else [],
                "device": data.get("devices", [])}
    except Exception as exc:
        return {"status": "offline", "available": False, "url": DEFAULT_URL,
                "message": f"ComfyUI local não está disponível ({type(exc).__name__}).",
                "setup": "Instale ComfyUI e um checkpoint SD 1.5 ou compatível; mantenha o servidor local em 127.0.0.1:8188."}


def _workflow(prompt: str, checkpoint: str, width: int, height: int, steps: int, seed: int) -> dict:
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "low quality, blurry, distorted, watermark, text artifacts", "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": steps, "cfg": 7.0, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0, "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": "MYRA", "images": ["6", 0]}},
    }


def generate(prompt: str, checkpoint: str = "", width: int = 512, height: int = 512,
             steps: int = 25, timeout: int = 600) -> dict:
    prompt = str(prompt or "").strip()
    if not prompt or len(prompt) > 4000:
        return {"status": "error", "message": "Descreva a imagem (até 4.000 caracteres)."}
    width = max(256, min(1024, int(width) // 64 * 64))
    height = max(256, min(1024, int(height) // 64 * 64))
    steps = max(1, min(50, int(steps)))
    current = status()
    if not current.get("available"):
        return current
    available = current.get("checkpoints") or []
    chosen = checkpoint.strip() if checkpoint else (available[0] if available else "")
    if not chosen or chosen not in available:
        return {"status": "error", "message": "Nenhum checkpoint válido foi encontrado no ComfyUI.", "available_checkpoints": available}
    client_id = secrets.token_hex(16)
    try:
        response = requests.post(f"{DEFAULT_URL}/prompt", json={"prompt": _workflow(prompt, chosen, width, height, steps, secrets.randbelow(2**32)), "client_id": client_id}, timeout=15)
        response.raise_for_status()
        prompt_id = response.json().get("prompt_id")
        if not prompt_id:
            return {"status": "error", "message": "ComfyUI não retornou prompt_id."}
        deadline = time.monotonic() + max(30, min(int(timeout), 900))
        history: dict[str, Any] = {}
        while time.monotonic() < deadline:
            time.sleep(1.5)
            check = requests.get(f"{DEFAULT_URL}/history/{prompt_id}", timeout=10)
            check.raise_for_status()
            history = check.json().get(prompt_id, {})
            outputs = history.get("outputs", {})
            saved = next((item for node in outputs.values() for item in node.get("images", [])), None)
            if saved:
                image = requests.get(f"{DEFAULT_URL}/view", params=saved, timeout=60)
                image.raise_for_status()
                content = image.content
                if len(content) > 24 * 1024 * 1024:
                    return {"status": "error", "message": "A imagem gerada excede o limite de transporte de 24 MB."}
                mime = image.headers.get("Content-Type", "image/png").split(";", 1)[0]
                encoded = base64.b64encode(content).decode("ascii")
                return {"status": "ok", "provider": "ComfyUI local", "model": chosen,
                        "prompt_id": prompt_id, "filename": saved.get("filename", "MYRA.png"),
                        "mime_type": mime, "data_url": f"data:{mime};base64,{encoded}",
                        "width": width, "height": height}
            if history.get("status", {}).get("status_str") == "error":
                return {"status": "error", "message": "ComfyUI informou falha ao executar o workflow.", "details": history.get("status", {}).get("messages", [])[-2:]}
        return {"status": "timeout", "prompt_id": prompt_id, "message": "A geração continua ou excedeu o tempo de espera. Consulte a fila do ComfyUI."}
    except requests.RequestException as exc:
        return {"status": "error", "message": f"Falha ao comunicar com ComfyUI: {type(exc).__name__}."}
