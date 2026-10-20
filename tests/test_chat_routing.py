from __future__ import annotations

import json
import agent
import tasks.simple_task as simple_task


def test_questions_do_not_trigger_computer_actions():
    assert agent._myra_explicit_action("Como funciona o Google?") is False
    assert agent._myra_explicit_action("O que é automação?") is False
    assert agent._myra_explicit_action("What is an AI agent?") is False


def test_explicit_computer_commands_are_routed():
    assert agent._myra_explicit_action("Abra o Google")
    assert agent._myra_explicit_action("Pesquise na web sobre robótica")
    assert agent._myra_explicit_action("Open GitHub")
    assert agent._myra_explicit_action("Pesquise no YouTube sobre robótica")


def test_task_followup_commands_are_classified():
    assert agent._myra_control_intent("Qual o status da tarefa?") == "status"
    assert agent._myra_control_intent("Como está a tarefa?") == "status"
    assert agent._myra_control_intent("Cancele a tarefa atual") == "cancel"
    assert agent._myra_control_intent("Pause a tarefa") == "pause"
    assert agent._myra_control_intent("Retome a tarefa abc123") == "resume:abc123"
    assert agent._myra_control_intent("Como faço uma tarefa?") is None


def test_memory_persists_and_is_separated_by_chat(monkeypatch, tmp_path):
    monkeypatch.setattr(agent, "_MYRA_CHAT_MEMORY_PATH", tmp_path / "memory.json")
    agent._myra_memory_turn("user-a:chat-1", "user", "Minha preferência é português.")
    agent._myra_memory_turn("user-a:chat-2", "user", "Outro contexto.")
    agent._myra_memory_turn("user-b:chat-1", "user", "Contexto de outra pessoa.")

    restored = agent._myra_memory_read()
    assert restored["user-a:chat-1"][0]["content"] == "Minha preferência é português."
    assert restored["user-a:chat-2"][0]["content"] == "Outro contexto."
    assert restored["user-b:chat-1"][0]["content"] == "Contexto de outra pessoa."
    assert restored["user-a:chat-1"] != restored["user-a:chat-2"]


def test_openai_endpoint_forwards_identity_headers_to_memory_key(monkeypatch):
    from fastapi.testclient import TestClient

    captured = {}

    async def fake_route(data, messages, user_msg, model):
        captured["key"] = agent._myra_chat_key(data, messages)
        return "ok"

    monkeypatch.setattr(agent, "_myra_route_message", fake_route)
    with TestClient(agent.app) as client:
        response = client.post(
            "/v1/chat/completions",
            headers={
                "x-openwebui-chat-id": "endpoint-chat",
                "x-openwebui-user-id": "endpoint-user",
            },
            json={"model": "myra-agent", "messages": [{"role": "user", "content": "Olá"}]},
        )

    assert response.status_code == 200
    assert captured["key"] == "endpoint-user:endpoint-chat"


def test_identity_headers_are_used_when_provider_sends_them():
    payload = {"model": "myra-agent", "messages": []}
    enriched = agent._myra_apply_identity_headers(
        payload,
        {"x-openwebui-chat-id": "chat-from-header", "x-openwebui-user-id": "user-from-header"},
    )
    assert agent._myra_chat_key(enriched, []) == "user-from-header:chat-from-header"

    # Explicit body metadata must take precedence over optional headers.
    payload = {"metadata": {"chat_id": "body-chat", "user_id": "body-user"}}
    enriched = agent._myra_apply_identity_headers(
        payload, {"x-chat-id": "header-chat", "x-user-id": "header-user"}
    )
    assert agent._myra_chat_key(enriched, []) == "body-user:body-chat"


def test_chat_key_prefers_explicit_id_and_falls_back_to_stable_conversation_fingerprint():
    assert agent._myra_chat_key(
        {"metadata": {"chat_id": "chat-123", "user_id": "user-a"}},
        [{"role": "user", "content": "Olá"}],
    ) == "user-a:chat-123"

    first_turn = [{"role": "user", "content": "Quero aprender robótica."}]
    later_turn = [
        {"role": "user", "content": "Quero aprender robótica."},
        {"role": "assistant", "content": "Vamos começar pelos fundamentos."},
        {"role": "user", "content": "Qual é o primeiro passo?"},
    ]
    first_key = agent._myra_chat_key({"user": "user-a"}, first_turn)
    assert first_key == agent._myra_chat_key({"user": "user-a"}, later_turn)
    assert first_key is not None
    assert first_key != agent._myra_chat_key(
        {"user": "user-a"}, [{"role": "user", "content": "Quero aprender inglês."}]
    )
    assert agent._myra_chat_key({}, []) is None


def test_planner_browser_tools_use_playwright_not_real_chrome(monkeypatch):
    captured = {}

    def fake_llm(prompt, system=""):
        captured["prompt"] = prompt
        return json.dumps({
            "acao": "chamar",
            "ferramenta": "browser_new_tab",
            "args": {"url": "https://example.com"},
            "motivo": "abrir com Playwright isolado",
        })

    monkeypatch.setattr(simple_task, "_llm", fake_llm)
    decision = simple_task._decidir_proximo_passo("Abra https://example.com", [])

    assert decision["ferramenta"] == "browser_new_tab"
    assert "browser_new_tab:" in captured["prompt"]
    assert "Playwright isolado" in captured["prompt"]
    assert "playwright_open_url:" not in captured["prompt"]
    assert simple_task.FERRAMENTAS_DISPONIVEIS["browser_new_tab"].__name__ == "_t_browser_new_tab"


def test_synthesis_history_preserves_structured_browser_metadata():
    history = [{
        "passo": 2,
        "ferramenta": "browser_new_tab",
        "args": {"url": "https://example.com"},
        "ok": True,
        "resultado": {
            "status": "ok",
            "result": "Abri https://example.com em uma nova página Playwright.",
            "url": "https://example.com/",
            "title": "Example Domain",
        },
    }]

    rendered = simple_task._formatar_historico(history)
    assert '"title": "Example Domain"' in rendered
    assert '"url": "https://example.com/"' in rendered
