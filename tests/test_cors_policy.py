from fastapi.testclient import TestClient

import agent


def _preflight(client, origin):
    return client.options(
        "/",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )


def test_cors_allows_native_tauri_origin(monkeypatch):
    monkeypatch.setattr(agent, "_telegram_startup", lambda: None)
    monkeypatch.setattr(agent, "_telegram_shutdown", lambda: None)

    with TestClient(agent.app) as client:
        response = _preflight(client, "http://tauri.localhost")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://tauri.localhost"
    assert "*" not in response.headers["access-control-allow-origin"]


def test_cors_rejects_untrusted_web_origins(monkeypatch):
    monkeypatch.setattr(agent, "_telegram_startup", lambda: None)
    monkeypatch.setattr(agent, "_telegram_shutdown", lambda: None)

    with TestClient(agent.app) as client:
        response = _preflight(client, "https://attacker.example")

    assert response.status_code == 403
    assert "access-control-allow-origin" not in response.headers


def test_cors_allows_local_development_origin(monkeypatch):
    monkeypatch.setattr(agent, "_telegram_startup", lambda: None)
    monkeypatch.setattr(agent, "_telegram_shutdown", lambda: None)

    with TestClient(agent.app) as client:
        response = _preflight(client, "http://localhost:1420")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:1420"


def test_untrusted_origin_is_rejected_even_without_cors_preflight(monkeypatch):
    monkeypatch.setattr(agent, "_telegram_startup", lambda: None)
    monkeypatch.setattr(agent, "_telegram_shutdown", lambda: None)

    with TestClient(agent.app) as client:
        response = client.get("/", headers={"Origin": "https://attacker.example"})

    assert response.status_code == 403
    assert "Origem não autorizada" in response.json()["detail"]


def test_requests_without_browser_origin_remain_available_for_local_cli(monkeypatch):
    monkeypatch.setattr(agent, "_telegram_startup", lambda: None)
    monkeypatch.setattr(agent, "_telegram_shutdown", lambda: None)

    with TestClient(agent.app) as client:
        response = client.get("/")

    assert response.status_code == 200
