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
