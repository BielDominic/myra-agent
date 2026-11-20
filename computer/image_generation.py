"""Local image generation and image-to-image editing via ComfyUI."""
from __future__ import annotations

import base64
import os
import secrets
import time
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Any

import requests
from PIL import Image

DEFAULT_URL = os.environ.get("MYRA_COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
NEGATIVE_PROMPT = (
    "low quality, blurry, pixelated, jpeg artifacts, distorted, deformed, "
    "bad anatomy, malformed hands, extra fingers, watermark, text, logo"
)


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
    """Higher quality SD 1.5 workflow tuned to stay practical on 4 GB VRAM."""
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": NEGATIVE_PROMPT, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": steps, "cfg": 6.5,
            "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0,
            "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": "MYRA", "images": ["6", 0]}},
    }


def _edit_workflow(prompt: str, checkpoint: str, image_name: str, width: int,
                   height: int, steps: int, seed: int, denoise: float = 0.45) -> dict:
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": NEGATIVE_PROMPT, "clip": ["1", 1]}},
        "4": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "5": {"class_type": "VAEEncode", "inputs": {"pixels": ["4", 0], "vae": ["1", 2]}},
        "6": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": steps, "cfg": 6.0,
            "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": denoise,
            "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["5", 0]}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"filename_prefix": "MYRA_EDIT", "images": ["7", 0]}},
    }


def _submit_and_wait(workflow: dict, checkpoint: str, timeout: int, width: int, height: int) -> dict:
    try:
        response = requests.post(f"{DEFAULT_URL}/prompt",
            json={"prompt": workflow, "client_id": secrets.token_hex(16)}, timeout=15)
        response.raise_for_status()
        prompt_id = response.json().get("prompt_id")
        if not prompt_id:
            return {"status": "error", "message": "ComfyUI não retornou prompt_id."}
        deadline = time.monotonic() + max(30, min(int(timeout), 900))
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
                if not content or len(content) > 24 * 1024 * 1024:
                    return {"status": "error", "message": "A imagem retornada excede o limite de 24 MB ou está vazia."}
                mime = image.headers.get("Content-Type", "image/png").split(";", 1)[0]
                encoded = base64.b64encode(content).decode("ascii")
                return {"status": "ok", "provider": "ComfyUI local", "model": checkpoint,
                        "prompt_id": prompt_id, "filename": saved.get("filename", "MYRA.png"),
                        "mime_type": mime, "data_url": f"data:{mime};base64,{encoded}",
                        "width": width, "height": height}
            if history.get("status", {}).get("status_str") == "error":
                return {"status": "error", "message": "ComfyUI informou falha ao executar o workflow.",
                        "details": history.get("status", {}).get("messages", [])[-2:]}
        return {"status": "timeout", "prompt_id": prompt_id,
                "message": "A geração continua ou excedeu o tempo de espera. Consulte a fila do ComfyUI."}
    except requests.RequestException as exc:
        return {"status": "error", "message": f"Falha ao comunicar com ComfyUI: {type(exc).__name__}."}


def _choose_checkpoint(checkpoint: str, available: list) -> str:
    chosen = checkpoint.strip() if checkpoint else (available[0] if available else "")
    return chosen if chosen and chosen in available else ""


def generate(prompt: str, checkpoint: str = "", width: int = 640, height: int = 640,
             steps: int = 30, timeout: int = 600) -> dict:
    prompt = str(prompt or "").strip()
    if not prompt or len(prompt) > 4000:
        return {"status": "error", "message": "Descreva a imagem (até 4.000 caracteres)."}
    width = max(256, min(768, int(width) // 64 * 64))
    height = max(256, min(768, int(height) // 64 * 64))
    steps = max(20, min(40, int(steps)))
    current = status()
    if not current.get("available"):
        return current
    chosen = _choose_checkpoint(checkpoint, current.get("checkpoints") or [])
    if not chosen:
        return {"status": "error", "message": "Nenhum checkpoint válido foi encontrado no ComfyUI.",
                "available_checkpoints": current.get("checkpoints") or []}
    workflow = _workflow(prompt, chosen, width, height, steps, secrets.randbelow(2**32))
    return _submit_and_wait(workflow, chosen, timeout, width, height)


def _cleanup_uploaded_input(image_name: str) -> None:
    """Remove only MYRA-owned temporary uploads from ComfyUI's input directory."""
    root_value = os.environ.get("MYRA_COMFYUI_INPUT_DIR", "").strip()
    if root_value:
        root = Path(root_value).expanduser()
    else:
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            return
        root = Path(local_app_data) / "MYRA" / "ComfyUI" / "ComfyUI" / "input"
    try:
        relative = PurePosixPath(str(image_name or ""))
        if (not relative.parts or relative.is_absolute()
                or any(part in ("", ".", "..") for part in relative.parts)
                or "\\" in str(image_name)):
            return
        if not relative.name.startswith("myra_edit_") or relative.suffix.lower() != ".png":
            return
        resolved_root = root.resolve()
        target = (resolved_root.joinpath(*relative.parts)).resolve()
        target.relative_to(resolved_root)
        if target.is_file():
            target.unlink()
    except (OSError, ValueError):
        # Cleanup must never turn a completed edit into a failed request.
        return


def _photo_edit_prompt(prompt: str) -> str:
    return (
        f"Photorealistic edit: {prompt}. Preserve the original subject identity, "
        "pose, framing and all details not explicitly requested to change."
    )


def edit(image_bytes: bytes, filename: str, prompt: str, checkpoint: str = "",
         denoise: float = 0.45, steps: int = 28, timeout: int = 600) -> dict:
    """Edit an uploaded photo with img2img while retaining its composition."""
    prompt = str(prompt or "").strip()
    if not prompt or len(prompt) > 4000:
        return {"status": "error", "message": "Descreva a edição desejada (até 4.000 caracteres)."}
    if not image_bytes or len(image_bytes) > 12 * 1024 * 1024:
        return {"status": "error", "message": "A foto deve ter até 12 MB."}
    try:
        with Image.open(BytesIO(image_bytes)) as source:
            source.verify()
        with Image.open(BytesIO(image_bytes)) as source:
            source = source.convert("RGB")
            source.thumbnail((768, 768), Image.Resampling.LANCZOS)
            width = max(64, (source.width // 64) * 64)
            height = max(64, (source.height // 64) * 64)
            source = source.resize((width, height), Image.Resampling.LANCZOS)
            buffer = BytesIO()
            source.save(buffer, format="PNG", optimize=True)
            normalized = buffer.getvalue()
    except Exception:
        return {"status": "error", "message": "O arquivo enviado não é uma imagem válida."}
    current = status()
    if not current.get("available"):
        return current
    chosen = _choose_checkpoint(checkpoint, current.get("checkpoints") or [])
    if not chosen:
        return {"status": "error", "message": "Nenhum checkpoint válido foi encontrado no ComfyUI.",
                "available_checkpoints": current.get("checkpoints") or []}
    safe_name = f"myra_edit_{secrets.token_hex(12)}.png"
    try:
        uploaded = requests.post(f"{DEFAULT_URL}/upload/image",
            files={"image": (safe_name, normalized, "image/png")},
            data={"type": "input", "overwrite": "false"}, timeout=60)
        uploaded.raise_for_status()
        upload_data = uploaded.json()
        image_name = str(upload_data.get("name") or "")
        subfolder = str(upload_data.get("subfolder") or "").strip("/")
        if not image_name or "/" in image_name or "\\" in image_name:
            return {"status": "error", "message": "ComfyUI retornou um nome de imagem inválido."}
        if subfolder:
            image_name = f"{subfolder}/{image_name}"
        denoise = max(0.2, min(0.75, float(denoise)))
        steps = max(20, min(36, int(steps)))
        edit_prompt = _photo_edit_prompt(prompt)
        workflow = _edit_workflow(edit_prompt, chosen, image_name, width, height, steps,
                                  secrets.randbelow(2**32), denoise)
        result = _submit_and_wait(workflow, chosen, timeout, width, height)
        if result.get("status") == "ok":
            result["edited"] = True
            result["source_dimensions"] = [width, height]
        if result.get("status") in ("ok", "error"):
            _cleanup_uploaded_input(image_name)
        return result
    except (requests.RequestException, ValueError, TypeError) as exc:
        return {"status": "error", "message": f"Falha na edição local: {type(exc).__name__}."}
