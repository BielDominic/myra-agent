from computer.image_generation import _workflow

def test_sdxl_workflow_is_complete_and_uses_requested_settings():
    workflow = _workflow("A cinematic lighthouse", "sd15.safetensors", 512, 768, 20, 12345)
    assert workflow["1"]["inputs"]["ckpt_name"] == "sd15.safetensors"
    assert workflow["2"]["inputs"]["text"] == "A cinematic lighthouse"
    assert workflow["4"]["inputs"]["width"] == 512
    assert workflow["4"]["inputs"]["height"] == 768
    assert workflow["5"]["inputs"]["steps"] == 20
    assert workflow["5"]["inputs"]["seed"] == 12345
    assert workflow["7"]["class_type"] == "SaveImage"

def test_sdxl_workflow_has_connected_model_and_latent_nodes():
    workflow = _workflow("test", "sd15.safetensors", 512, 512, 8, 1)
    assert workflow["5"]["inputs"]["model"] == ["1", 0]
    assert workflow["5"]["inputs"]["positive"] == ["2", 0]
    assert workflow["5"]["inputs"]["negative"] == ["3", 0]
    assert workflow["5"]["inputs"]["latent_image"] == ["4", 0]
    assert workflow["6"]["inputs"]["samples"] == ["5", 0]


def test_generation_uses_quality_sampler_and_vram_friendly_defaults():
    workflow = _workflow("Photorealistic portrait, natural light", "dreamshaper.safetensors", 640, 640, 30, 99)
    sampler = workflow["5"]["inputs"]
    assert sampler["sampler_name"] == "dpmpp_2m_sde"
    assert sampler["scheduler"] == "karras"
    assert sampler["steps"] == 30
    assert sampler["cfg"] == 5.5
    assert workflow["4"]["inputs"]["width"] == 640


def test_img2img_workflow_keeps_uploaded_photo_as_latent_source():
    from computer.image_generation import _edit_workflow
    workflow = _edit_workflow("Add a red jacket", "dreamshaper.safetensors", "myra/photo.png", 640, 512, 28, 123, 0.4)
    assert workflow["4"]["class_type"] == "LoadImage"
    assert workflow["4"]["inputs"]["image"] == "myra/photo.png"
    assert workflow["5"]["class_type"] == "VAEEncode"
    sampler = workflow["6"]["inputs"]
    assert sampler["latent_image"] == ["5", 0]
    assert sampler["denoise"] == 0.4
    assert sampler["sampler_name"] == "dpmpp_2m"
    assert workflow["8"]["class_type"] == "SaveImage"


def test_status_reports_offline_comfyui_without_crashing(monkeypatch):
    import requests
    from computer import image_generation
    def unavailable(*args, **kwargs):
        raise requests.ConnectionError("offline")
    monkeypatch.setattr(image_generation.requests, "get", unavailable)
    result = image_generation.status()
    assert result["status"] == "offline"
    assert result["available"] is False
    assert "ComfyUI" in result["message"]


def test_comfyui_cleanup_removes_only_myra_owned_uploads(tmp_path, monkeypatch):
    from computer.image_generation import _cleanup_uploaded_input

    monkeypatch.setenv("MYRA_COMFYUI_INPUT_DIR", str(tmp_path))
    owned = tmp_path / "myra_edit_0123456789abcdef01234567.png"
    unrelated = tmp_path / "family_photo.png"
    owned.write_bytes(b"temporary")
    unrelated.write_bytes(b"keep")

    _cleanup_uploaded_input(owned.name)
    _cleanup_uploaded_input(unrelated.name)
    _cleanup_uploaded_input("../outside.png")

    assert not owned.exists()
    assert unrelated.read_bytes() == b"keep"


def test_photo_edit_prompt_preserves_unrequested_details():
    from computer.image_generation import _photo_edit_prompt
    prompt = _photo_edit_prompt("Change the shirt to blue")
    assert prompt.startswith("Photorealistic edit: Change the shirt to blue")
    assert "Preserve the original subject identity" in prompt
    assert "all details not explicitly requested to change" in prompt


def test_edit_cleans_comfyui_temporary_upload_after_success(tmp_path, monkeypatch):
    from io import BytesIO
    from PIL import Image
    from computer import image_generation

    source = BytesIO()
    Image.new("RGB", (128, 128), (80, 100, 120)).save(source, format="PNG")
    monkeypatch.setenv("MYRA_COMFYUI_INPUT_DIR", str(tmp_path))
    monkeypatch.setattr(image_generation, "status", lambda: {
        "status": "ok", "available": True, "checkpoints": ["dreamshaper.safetensors"],
    })

    uploaded_names = []
    class UploadResponse:
        def raise_for_status(self): pass
        def json(self): return {"name": uploaded_names[-1], "subfolder": ""}

    def fake_upload(url, files, data, timeout):
        name, payload, mime = files["image"]
        uploaded_names.append(name)
        (tmp_path / name).write_bytes(payload)
        return UploadResponse()

    captured = {}
    def fake_wait(workflow, checkpoint, timeout, width, height):
        captured.update(workflow=workflow)
        return {"status": "ok", "filename": "MYRA_EDIT.png"}

    monkeypatch.setattr(image_generation.requests, "post", fake_upload)
    monkeypatch.setattr(image_generation, "_submit_and_wait", fake_wait)

    result = image_generation.edit(source.getvalue(), "photo.png", "Change the shirt to blue")

    assert result["status"] == "ok"
    assert result["edited"] is True
    assert not (tmp_path / uploaded_names[0]).exists()
    assert "Preserve the original subject identity" in captured["workflow"]["2"]["inputs"]["text"]


def test_prompt_enhancement_preserves_explicit_visual_attributes(monkeypatch):
    from computer import image_generation

    captured = {}
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {"response": "A nude blonde woman"}

    def fake_post(url, json, timeout):
        captured.update(url=url, payload=json, timeout=timeout)
        return Response()

    monkeypatch.setattr(image_generation.requests, "post", fake_post)
    enhanced, status = image_generation._enhance_prompt("Gere a imagem de uma loira pelada")

    assert enhanced == "A nude blonde woman"
    assert status == "ollama_local"
    assert captured["payload"]["options"]["num_gpu"] == 0
    assert captured["payload"]["keep_alive"] == 0
    assert "literal translator" in captured["payload"]["system"]
    assert "Never add a location, pose, clothing" in captured["payload"]["system"]


def test_prompt_enhancement_falls_back_to_original_when_ollama_is_offline(monkeypatch):
    import requests
    from computer import image_generation

    def unavailable(*args, **kwargs):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(image_generation.requests, "post", unavailable)
    original = "A blonde woman in a forest"
    enhanced, status = image_generation._enhance_prompt(original)

    assert enhanced == original
    assert status == "fallback_original_prompt"


def test_prompt_enhancement_can_be_disabled(monkeypatch):
    from computer import image_generation

    monkeypatch.setenv("MYRA_IMAGE_PROMPT_ENHANCER", "0")
    enhanced, status = image_generation._enhance_prompt("Uma mulher loira")

    assert enhanced == "Uma mulher loira"
    assert status == "disabled"


def test_realistic_vision_workflow_uses_external_vae_when_available():
    workflow = _workflow(
        "A photorealistic portrait", "Realistic_Vision_V6.safetensors",
        512, 768, 30, 123, "vae-ft-mse-840000-ema-pruned.safetensors",
    )

    assert workflow["8"]["class_type"] == "VAELoader"
    assert workflow["8"]["inputs"]["vae_name"] == "vae-ft-mse-840000-ema-pruned.safetensors"
    assert workflow["6"]["inputs"]["vae"] == ["8", 0]
    assert workflow["5"]["inputs"]["sampler_name"] == "dpmpp_2m_sde"


def test_negative_prompt_only_suppresses_nudity_when_not_requested():
    from computer.image_generation import NEGATIVE_PROMPT, _negative_prompt_for

    ordinary = _negative_prompt_for("A photorealistic blonde woman portrait")
    requested = _negative_prompt_for("A nude blonde woman")
    portuguese = _negative_prompt_for("Uma loira pelada")

    assert "nude, naked, topless" in ordinary
    assert "nude, naked, topless" not in requested
    assert "nude, naked, topless" not in portuguese
    assert "cgi, 3d render" in NEGATIVE_PROMPT
