import asyncio

import pytest
from fastapi import HTTPException

import agent


@pytest.mark.parametrize("state", ["running", "paused", "pausado"])
def test_chat_model_cannot_change_during_active_or_paused_task(monkeypatch, state):
    monkeypatch.setitem(agent._widget_status, "state", state)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(agent.myra_select_chat_model({"model": "model-that-does-not-exist"}))
    assert exc.value.status_code == 409
    assert "tarefa" in exc.value.detail.lower()


def test_github_workspace_requires_explicit_user_project_path():
    with pytest.raises(HTTPException) as exc:
        agent._myra_resolve_project_repo("")
    assert exc.value.status_code == 400
    assert "projeto" in exc.value.detail.lower()
