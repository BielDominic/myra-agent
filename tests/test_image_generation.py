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
