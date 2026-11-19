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


def test_planner_browser_tools_use_real_chrome_bridge(monkeypatch):
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
    assert "Playwright isolado" not in captured["prompt"]
    assert "playwright_open_url:" not in captured["prompt"]
    assert simple_task.FERRAMENTAS_DISPONIVEIS["browser_new_tab"].__module__ == "tasks.browser_bridge"


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


def test_composite_open_app_and_search_routes_each_step_deterministically(monkeypatch):
    tools = {
        "pc_open_application": lambda nome: {"status": "ok", "nome": nome},
        "pc_focus_window": lambda titulo: {"status": "ok", "titulo": titulo},
        "pc_hotkey": lambda keys: {"status": "ok", "keys": keys},
        "pc_type_text": lambda text: {"status": "ok", "text": text},
        "pc_press_key": lambda key: {"status": "ok", "key": key},
    }
    for name, fn in tools.items():
        monkeypatch.setitem(simple_task.FERRAMENTAS_DISPONIVEIS, name, fn)

    objective = "abra o Microsoft To Do e pesquise forza"
    expected = [
        ("pc_open_application", {"nome": "microsoft to do"}),
        ("pc_focus_window", {"titulo": "microsoft to do"}),
        ("pc_hotkey", {"keys": ["ctrl", "e"]}),
        ("pc_type_text", {"text": "forza"}),
        ("pc_press_key", {"key": "enter"}),
    ]
    history = []
    for tool, args in expected:
        decision = simple_task._decidir_proximo_passo(objective, history)
        assert decision["acao"] == "chamar"
        assert decision["ferramenta"] == tool
        assert decision["args"] == args
        history.append({"ok": True, "ferramenta": tool, "args": args, "resultado": {"status": "ok"}})


def test_composite_open_app_and_search_does_not_advance_after_failed_step(monkeypatch):
    for name in ("pc_open_application", "pc_hotkey", "pc_type_text", "pc_press_key"):
        monkeypatch.setitem(simple_task.FERRAMENTAS_DISPONIVEIS, name, lambda **kwargs: {"status": "ok"})
    objective = "abra o Microsoft To Do e pesquise forza"
    history = [{"passo": 1, "ok": False, "ferramenta": "pc_open_application", "args": {"nome": "microsoft to do"}, "resultado": None, "erro": "falhou"}]
    monkeypatch.setattr(simple_task, "_llm", lambda *args, **kwargs: json.dumps({"acao": "finalizar", "motivo": "teste fallback"}))
    decision = simple_task._decidir_proximo_passo(objective, history)
    assert decision["acao"] == "finalizar"


def test_app_search_intent_accepts_different_natural_language_phrasings():
    cases = [
        ("Entre no Microsoft Store e pesquise Minecraft", ("microsoft store", "minecraft")),
        ("Abra a loja da Microsoft e procure por Minecraft", ("microsoft store", "minecraft")),
        ("Quero que abra a Microsoft Store e busque Minecraft", ("microsoft store", "minecraft")),
        ("Acesse a Microsoft Store e encontre Minecraft", ("microsoft store", "minecraft")),
        ("Visite a Microsoft Store e veja se tem Minecraft", ("microsoft store", "minecraft")),
        ("Por favor, entre na Microsoft Store e pesquisar Minecraft", ("microsoft store", "minecraft")),
        ("Abra a Microsoft Store, pesquise Telegram Desktop, abra a ficha do aplicativo e verifique se está instalado; se não estiver, instale e confirme pelo botão Abrir.", ("microsoft store", "telegram desktop")),
        ("Abra a Microsoft Store e pesquise Telegram Desktop e instale", ("microsoft store", "telegram desktop")),
    ]
    for phrase, expected in cases:
        assert simple_task._extrair_intencao_app_busca(phrase) == expected


def test_app_search_intent_is_used_for_same_deterministic_plan(monkeypatch):
    for name in ("pc_open_application", "pc_hotkey", "pc_type_text", "pc_press_key"):
        monkeypatch.setitem(simple_task.FERRAMENTAS_DISPONIVEIS, name, lambda **kwargs: {"status": "ok"})
    phrases = [
        "Entre no Microsoft Store e pesquise Minecraft",
        "Abra a loja da Microsoft e procure por Minecraft",
        "Quero que abra a Microsoft Store e busque Minecraft",
    ]
    for objective in phrases:
        decision = simple_task._decidir_proximo_passo(objective, [])
        assert decision["acao"] == "chamar"
        assert decision["ferramenta"] == "pc_open_application"
        assert decision["args"]["nome"] in {"microsoft store", "loja da microsoft"}



def test_multiapp_open_routes_each_app_only_after_verified_success(monkeypatch):
    monkeypatch.setitem(simple_task.FERRAMENTAS_DISPONIVEIS, "pc_open_application",
                        lambda nome: {"status": "ok", "nome": nome})
    objective = "Abra o Bloco de Notas e a Calculadora"
    assert simple_task._extrair_intencao_multiapp(objective) == ["bloco de notas", "calculadora"]
    history = []
    first = simple_task._decidir_proximo_passo(objective, history)
    assert first["ferramenta"] == "pc_open_application"
    assert first["args"] == {"nome": "bloco de notas"}
    history.append({"ok": True, "ferramenta": first["ferramenta"], "args": first["args"],
                    "resultado": {"status": "ok", "nome": "Bloco de Notas"}})
    second = simple_task._decidir_proximo_passo(objective, history)
    assert second["ferramenta"] == "pc_open_application"
    assert second["args"] == {"nome": "calculadora"}
    history.append({"ok": True, "ferramenta": second["ferramenta"], "args": second["args"],
                    "resultado": {"status": "ok", "nome": "Calculadora"}})
    final = simple_task._decidir_proximo_passo(objective, history)
    assert final["acao"] == "finalizar"
    assert "Bloco de Notas, Calculadora" in final["resultado"]


def test_unverified_control_action_is_never_retried(monkeypatch):
    calls = []
    def click(**kwargs):
        calls.append(kwargs)
        return {"status": "unverified", "verified": False, "result": "effect not observable"}
    monkeypatch.setitem(simple_task.FERRAMENTAS_DISPONIVEIS, "pc_control_action", click)
    result = simple_task._executar_passo("pc_control_action", {
        "titulo": "Example", "alvo": "Install", "acao": "click"
    }, tentativas=3)
    assert result["ok"] is False
    assert result["resultado"]["status"] == "unverified"
    assert len(calls) == 1


def test_ambiguous_control_action_is_never_retried(monkeypatch):
    calls = []
    def click(**kwargs):
        calls.append(kwargs)
        return {"status": "ambiguous", "result": ["Install", "Install for all"]}
    monkeypatch.setitem(simple_task.FERRAMENTAS_DISPONIVEIS, "pc_control_action", click)
    result = simple_task._executar_passo("pc_control_action", {
        "titulo": "Example", "alvo": "Install", "acao": "click"
    }, tentativas=3)
    assert result["ok"] is False
    assert result["resultado"]["status"] == "ambiguous"
    assert len(calls) == 1


def test_store_instalacao_so_confirma_com_telegram_e_botao_abrir_visiveis():
    confirmar = simple_task._store_controles_confirmam_instalacao_telegram
    controles_validos = [
        {"nome": "Telegram Desktop", "control_type": "Text", "visible": True, "enabled": True},
        {"nome": "Open", "control_type": "Button", "visible": True, "enabled": True},
    ]
    assert confirmar(controles_validos) is True
    assert confirmar([
        {"nome": "Notepad", "control_type": "Text", "visible": True, "enabled": True},
        {"nome": "Open", "control_type": "Button", "visible": True, "enabled": True},
    ]) is False
    assert confirmar([
        {"nome": "Telegram Desktop", "control_type": "Text", "visible": True, "enabled": True},
        {"nome": "Open", "control_type": "Button", "visible": False, "enabled": True},
    ]) is False
    assert confirmar(None) is False


def test_store_instalacao_reconhece_rotulos_localizados_e_id_de_pacote():
    confirmar = simple_task._store_controles_confirmam_instalacao_telegram
    assert confirmar([
        {"nome": "Telegram Desktop", "control_type": "Text", "visible": True, "enabled": True},
        {"nome": chr(214) + "ffnen", "control_type": "Button", "visible": True, "enabled": True},
    ]) is True
    assert confirmar([
        {"nome": "TelegramMessengerLLP.TelegramDesktop", "control_type": "Text", "visible": True, "enabled": True},
        {"nome": "Ouvrir", "control_type": "Button", "visible": True, "enabled": True},
    ]) is True
    # Um botao com nome de acao diferente nao deve gerar falso positivo.
    assert confirmar([
        {"nome": "Telegram Desktop", "control_type": "Text", "visible": True, "enabled": True},
        {"nome": "Install", "control_type": "Button", "visible": True, "enabled": True},
    ]) is False
    # Na ficha real da Microsoft Store, o rótulo Open pode ser exposto como Text.
    assert confirmar([
        {"nome": "Telegram Desktop", "control_type": "Text", "visible": True, "enabled": True},
        {"nome": "Open", "control_type": "Text", "automation_id": "AcquisitionBlock", "visible": True, "enabled": True},
    ]) is True
    # Um texto Open genérico, sem o ID de estado da Store, não é prova suficiente.
    assert confirmar([
        {"nome": "Telegram Desktop", "control_type": "Text", "visible": True, "enabled": True},
        {"nome": "Open", "control_type": "Text", "automation_id": "Description", "visible": True, "enabled": True},
    ]) is False


def test_store_sintese_nao_contradiz_ficha_com_botao_open_confirmado():
    objetivo = (
        "Abra a Microsoft Store, pesquise Telegram Desktop, abra a ficha do aplicativo "
        "e verifique se está instalado; se não estiver, instale e confirme pelo botão Abrir."
    )
    historico = [
        {"ferramenta": "pc_press_key", "args": {"key": "enter"}, "ok": True},
        {
            "ferramenta": "pc_list_controls",
            "ok": True,
            "resultado": {"result": [
                {"nome": "Telegram Desktop", "control_type": "Text", "visible": True, "enabled": True},
                {"nome": "Open", "control_type": "Button", "automation_id": "OpenInstalledProduct",
                 "visible": True, "enabled": True},
            ]},
        },
    ]
    resposta = simple_task._sintetizar(objetivo, historico)
    assert "ja esta instalado" in resposta
    assert "Open/Abrir" in resposta
    assert "nao foi possivel instalar" not in resposta


def test_store_resultados_so_confirmam_instalacao_com_card_exato_installed():
    confirmar = simple_task._store_resultados_confirmam_telegram_instalado
    assert confirmar([
        {"nome": "Telegram Desktop. 7 total ratings. Average rating of 4.7 out of five stars. Installed ",
         "control_type": "Button", "visible": True, "enabled": True},
    ]) is True
    assert confirmar([
        {"nome": "Telegram Desktop. 7 total ratings. Average rating of 4.7 out of five stars. Owned ",
         "control_type": "Button", "visible": True, "enabled": True},
    ]) is False
    assert confirmar([
        {"nome": "WhatsApp. 7 total ratings. Installed", "control_type": "Button", "visible": True, "enabled": True},
    ]) is False
    assert confirmar([
        {"nome": "Telegram Desktop. 7 total ratings. Installed", "control_type": "Button", "visible": False, "enabled": True},
    ]) is False


def test_multiapp_open_stops_after_unverified_or_failed_step(monkeypatch):
    monkeypatch.setitem(simple_task.FERRAMENTAS_DISPONIVEIS, "pc_open_application",
                        lambda nome: {"status": "ok", "nome": nome})
    objective = "Abra o Bloco de Notas e a Calculadora"
    history = [{"ok": True, "ferramenta": "pc_open_application",
                "args": {"nome": "bloco de notas"},
                "resultado": {"status": "erro", "result": "atalho n?o encontrado"}}]
    decision = simple_task._decidir_proximo_passo(objective, history)
    assert decision["acao"] == "finalizar"
    assert "interrompido" in decision["resultado"]


def test_browser_form_flow_is_planned_deterministically():
    objetivo = (
        "Abra http://127.0.0.1:8765, preencha o campo Your name com MYRA "
        "e clique em Send; confirme que a pagina mostra Sent: MYRA."
    )
    historico = []
    esperados = [
        ("browser_new_tab", {"url": "http://127.0.0.1:8765"}),
        ("browser_type_text", {"campo": "Your name", "texto": "MYRA"}),
        ("browser_click_text", {"descricao": "Send"}),
        ("browser_read_active_tab", {}),
    ]
    for ferramenta_esperada, args_esperados in esperados:
        passo = simple_task._decidir_proximo_passo(objetivo, historico)
        assert passo["acao"] == "chamar"
        assert passo["ferramenta"] == ferramenta_esperada
        assert passo["args"] == args_esperados
        historico.append({
            "ferramenta": ferramenta_esperada,
            "args": args_esperados,
            "ok": True,
            "resultado": {"status": "ok", "result": "passo simulado"},
        })


def test_multiapp_parser_does_not_capture_search_install_or_browser_flows():
    assert simple_task._extrair_intencao_multiapp("Abra o Microsoft To Do e pesquise forza") is None
    assert simple_task._extrair_intencao_multiapp("Abra a Microsoft Store e instale Telegram") is None
    assert simple_task._extrair_intencao_multiapp("Abra https://example.com") is None
    assert simple_task._extrair_intencao_multiapp(
        "Abra https://example.com no navegador e leia o título da página e o primeiro parágrafo."
    ) is None
    assert simple_task._extrair_intencao_multiapp("Abra o site example.com e leia a página atual") is None


def test_app_open_parser_strips_confirmation_clause_and_preserves_compound_routes():
    assert simple_task._extrair_intencao_app_abertura(
        "Abra a Calculadora do Windows e confirme que a janela está visível."
    ) == "calculadora do windows"
    assert simple_task._extrair_intencao_app_abertura(
        "Abra a Microsoft Store, pesquise Telegram Desktop e instale."
    ) is None
    assert simple_task._extrair_intencao_app_abertura(
        "Abra o Bloco de Notas e a Calculadora"
    ) is None



def test_application_open_supports_common_portuguese_aliases(monkeypatch):
    from computer import applications
    launched = []
    monkeypatch.setattr(applications, "listar_aplicativos", lambda: {
        "status": "ok", "total": 2, "result": [
            {"nome": "Notepad", "atalho": "shell:AppsFolder\\Microsoft.WindowsNotepad!App", "origem": "test"},
            {"nome": "Calculator", "atalho": "shell:AppsFolder\\Microsoft.WindowsCalculator!App", "origem": "test"},
        ]
    })
    monkeypatch.setattr(applications.os, "startfile", lambda target: launched.append(target), raising=False)
    monkeypatch.setattr(applications, "_verificar_janela_aplicativo", lambda nome: {"Notepad": "Untitled - Notepad", "Calculator": "Calculator"}.get(nome))
    resultado_notas = applications.abrir_aplicativo("bloco de notas")
    resultado_calc = applications.abrir_aplicativo("calculadora")
    resultado_calc_windows = applications.abrir_aplicativo("calculadora do windows")
    assert resultado_notas["status"] == "ok" and resultado_notas["verified"] is True
    assert resultado_calc["status"] == "ok" and resultado_calc["verified"] is True
    assert resultado_calc_windows["status"] == "ok" and resultado_calc_windows["verified"] is True
    assert len(launched) == 3


def test_application_open_reports_unverified_when_no_visible_window(monkeypatch):
    from computer import applications
    monkeypatch.setattr(applications, "listar_aplicativos", lambda: {"status": "ok", "total": 1, "result": [
        {"nome": "Example App", "atalho": "C:\\Apps\\example.exe", "origem": "test"}
    ]})
    launched = []
    monkeypatch.setattr(applications.os, "startfile", lambda target: launched.append(target), raising=False)
    monkeypatch.setattr(applications, "_verificar_janela_aplicativo", lambda nome: None)
    result = applications.abrir_aplicativo("Example App")
    assert launched == ["C:\\Apps\\example.exe"]
    assert result["status"] == "unverified"
    assert result["verified"] is False



def test_registry_inventory_never_uses_uninstall_command_as_launch_target(monkeypatch):
    from computer import applications
    monkeypatch.setattr(applications, "_atalhos_raiz", lambda: [])
    monkeypatch.setattr(applications, "_apps_menu_iniciar", lambda: [])
    monkeypatch.setattr(applications, "_apps_registro_desinstalacao", lambda: [
        {"nome": "Unsafe Registry App", "atalho": None, "origem": "Windows Uninstall Registry", "launchable": False}
    ])
    inventory = applications.listar_aplicativos()
    assert inventory["status"] == "ok"
    assert inventory["result"][0]["launchable"] is False
    assert applications.abrir_aplicativo("Unsafe Registry App")["status"] == "not_launchable"


def test_registry_inventory_deduplicates_start_menu_apps(monkeypatch):
    from computer import applications
    monkeypatch.setattr(applications, "_atalhos_raiz", lambda: [])
    monkeypatch.setattr(applications, "_apps_menu_iniciar", lambda: [
        {"nome": "Example App", "atalho": "shell:AppsFolder\\Example.App!App", "origem": "Windows StartApps"}
    ])
    monkeypatch.setattr(applications, "_apps_registro_desinstalacao", lambda: [
        {"nome": "Example App", "atalho": "C:\\Apps\\example.exe", "origem": "Windows Uninstall Registry", "launchable": True}
    ])
    inventory = applications.listar_aplicativos()
    assert len(inventory["result"]) == 1
    assert inventory["result"][0]["origem"] == "Windows StartApps"


def test_local_task_start_queues_background_execution(monkeypatch):
    from fastapi import BackgroundTasks
    monkeypatch.setattr(agent, "_remote_task_scheduled", False)
    monkeypatch.setattr(agent, "_widget_status", {**agent._widget_status, "state": "idle"})
    background = BackgroundTasks()

    result = agent.task_start(agent.TaskSimple(objetivo="Abra o Bloco de Notas", max_passos=8), background)

    assert result["status"] == "accepted"
    assert len(background.tasks) == 1
    assert background.tasks[0].func is agent._run_remote_task
    monkeypatch.setattr(agent, "_remote_task_scheduled", False)
