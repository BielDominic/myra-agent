

def test_image_api_persists_validated_image_for_small_desktop_history(monkeypatch, tmp_path):
    import base64
    from io import BytesIO
    from PIL import Image
    from fastapi.testclient import TestClient
    import agent

    buffer = BytesIO()
    Image.new("RGB", (8, 8), (30, 90, 180)).save(buffer, format="PNG")
    png = buffer.getvalue()
    data_url = "data:image/png;base64," + base64.b64encode(png).decode("ascii")

    monkeypatch.setattr(agent, "MYRA_GENERATED_IMAGES_DIR", tmp_path)
    monkeypatch.setattr(agent._myra_image_generation, "generate", lambda *a, **k: {
        "status": "ok", "filename": "MYRA.png", "data_url": data_url,
    })
    monkeypatch.setattr(agent, "_telegram_startup", lambda: None)
    monkeypatch.setattr(agent, "_telegram_shutdown", lambda: None)

    with TestClient(agent.app) as client:
        generated = client.post("/images/generate", json={
            "prompt": "A blue lighthouse", "provider": "comfyui",
        })
        assert generated.status_code == 200
        body = generated.json()
        assert body["data_url"] == data_url
        assert body["image_url"].startswith("http://127.0.0.1:8000/images/files/")
        assert len(body["image_id"]) == 32

        image_response = client.get("/images/files/" + body["image_id"])
        assert image_response.status_code == 200
        assert image_response.headers["content-type"] == "image/png"
        assert image_response.content == png

        invalid = client.get("/images/files/not-a-valid-image-id")
        assert invalid.status_code == 404


def test_image_api_rejects_invalid_generated_image_payload(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    import agent

    monkeypatch.setattr(agent, "MYRA_GENERATED_IMAGES_DIR", tmp_path)
    monkeypatch.setattr(agent._myra_image_generation, "generate", lambda *a, **k: {
        "status": "ok", "data_url": "data:image/png;base64,not-an-image",
    })
    monkeypatch.setattr(agent, "_telegram_startup", lambda: None)
    monkeypatch.setattr(agent, "_telegram_shutdown", lambda: None)

    with TestClient(agent.app) as client:
        response = client.post("/images/generate", json={
            "prompt": "Invalid image test", "provider": "comfyui",
        })

    assert response.status_code == 502
    assert not list(tmp_path.iterdir())


def test_desktop_image_request_omits_base64_when_local_file_url_is_available(monkeypatch, tmp_path):
    import base64
    from io import BytesIO
    from PIL import Image
    from fastapi.testclient import TestClient
    import agent

    buffer = BytesIO()
    Image.new("RGB", (4, 4), (20, 40, 60)).save(buffer, format="PNG")
    data_url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
    monkeypatch.setattr(agent, "MYRA_GENERATED_IMAGES_DIR", tmp_path)
    monkeypatch.setattr(agent._myra_image_generation, "generate", lambda *a, **k: {
        "status": "ok", "filename": "MYRA.png", "data_url": data_url,
    })
    monkeypatch.setattr(agent, "_telegram_startup", lambda: None)
    monkeypatch.setattr(agent, "_telegram_shutdown", lambda: None)

    with TestClient(agent.app) as client:
        response = client.post("/images/generate", json={
            "prompt": "Small image", "provider": "comfyui", "include_data_url": False,
        })

    assert response.status_code == 200
    assert response.json()["image_url"].startswith("http://127.0.0.1:8000/images/files/")
    assert "data_url" not in response.json()
