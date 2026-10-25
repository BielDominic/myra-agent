import pytest
from fastapi import HTTPException

from tasks.remote_api_auth import validar_token_remoto


def test_remote_api_is_disabled_without_secret(monkeypatch):
    monkeypatch.delenv("MYRA_REMOTE_API_TOKEN", raising=False)
    with pytest.raises(HTTPException) as exc:
        validar_token_remoto("Bearer any-token")
    assert exc.value.status_code == 503


@pytest.mark.parametrize("authorization", [None, "", "wrong-token", "Basic secret", "Bearer wrong"])
def test_remote_api_rejects_missing_or_invalid_bearer(monkeypatch, authorization):
    monkeypatch.setenv("MYRA_REMOTE_API_TOKEN", "test-secret-very-long")
    with pytest.raises(HTTPException) as exc:
        validar_token_remoto(authorization)
    assert exc.value.status_code == 401


def test_remote_api_accepts_only_matching_bearer_token(monkeypatch):
    monkeypatch.setenv("MYRA_REMOTE_API_TOKEN", "test-secret-very-long")
    assert validar_token_remoto("Bearer test-secret-very-long") is True
    assert validar_token_remoto("bearer test-secret-very-long") is True

def test_remote_api_routes_are_disabled_and_require_bearer(monkeypatch):
    from fastapi.testclient import TestClient
    import agent

    # Do not start a real Telegram poller from TestClient in a developer's environment.
    monkeypatch.setattr(agent, "_telegram_startup", lambda: None)
    monkeypatch.setattr(agent, "_telegram_shutdown", lambda: None)
    monkeypatch.delenv("MYRA_REMOTE_API_TOKEN", raising=False)
    with TestClient(agent.app) as client:
        assert client.get("/remote/v1/status").status_code == 503

        monkeypatch.setenv("MYRA_REMOTE_API_TOKEN", "test-secret-very-long")
        assert client.get("/remote/v1/status").status_code == 401
        response = client.get(
            "/remote/v1/status",
            headers={"Authorization": "Bearer test-secret-very-long"},
        )
        assert response.status_code == 200
        assert "state" in response.json()

        invalid_task = client.post(
            "/remote/v1/task",
            headers={"Authorization": "Bearer test-secret-very-long"},
            json={"objetivo": "   ", "max_passos": 3},
        )
        assert invalid_task.status_code == 422


def test_remote_api_rejects_invalid_task_payload_and_duplicate_task(monkeypatch):
    from fastapi.testclient import TestClient
    import agent

    monkeypatch.setenv("MYRA_REMOTE_API_TOKEN", "test-secret-very-long")
    # Do not start a real Telegram poller from this TestClient.
    monkeypatch.setattr(agent, "_telegram_startup", lambda: None)
    monkeypatch.setattr(agent, "_telegram_shutdown", lambda: None)
    headers = {"Authorization": "Bearer test-secret-very-long"}
    with TestClient(agent.app) as client:
        too_long = client.post(
            "/remote/v1/task", headers=headers,
            json={"objetivo": "x" * 1201, "max_passos": 3},
        )
        assert too_long.status_code == 422

        invalid_steps = client.post(
            "/remote/v1/task", headers=headers,
            json={"objetivo": "valid objective", "max_passos": 51},
        )
        assert invalid_steps.status_code == 422

        original_scheduled = agent._remote_task_scheduled
        original_state = agent._widget_status.get("state")
        try:
            agent._remote_task_scheduled = True
            duplicate = client.post(
                "/remote/v1/task", headers=headers,
                json={"objetivo": "valid objective", "max_passos": 3},
            )
            assert duplicate.status_code == 409
        finally:
            agent._remote_task_scheduled = original_scheduled
            agent._widget_status["state"] = original_state


def test_remote_cancel_endpoint_requires_bearer_and_does_not_echo_token(monkeypatch):
    from fastapi.testclient import TestClient
    import agent

    monkeypatch.setenv("MYRA_REMOTE_API_TOKEN", "test-secret-very-long")
    monkeypatch.setattr(agent, "task_cancel", lambda: {"status": "ok", "result": "cancel requested"})
    monkeypatch.setattr(agent, "_telegram_startup", lambda: None)
    monkeypatch.setattr(agent, "_telegram_shutdown", lambda: None)
    with TestClient(agent.app) as client:
        assert client.post("/remote/v1/cancel").status_code == 401
        response = client.post(
            "/remote/v1/cancel",
            headers={"Authorization": "Bearer test-secret-very-long"},
        )
        assert response.status_code == 200
        assert "test-secret-very-long" not in response.text
