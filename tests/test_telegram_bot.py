from pathlib import Path

from tasks.telegram_bot import TelegramBot


def test_research_prompt_requires_evidence_over_source_reputation():
    """Research instructions should assess claims, not blindly trust institutional reputation."""
    import inspect
    import tasks.telegram_bot as telegram_bot_module

    source = inspect.getsource(telegram_bot_module.TelegramBot._handle_web_question)
    required_principles = (
        "NAO TRATE REPUTACAO COMO PROVA",
        "evidencia concreta apresentada",
        "evidencia contraria",
        "corroboracoes independentes",
        "Nao crie falsa equivalencia",
        "conclua que e inconclusivo",
    )
    for principle in required_principles:
        assert principle in source, f"Missing critical research principle: {principle}"


def test_general_chat_prompt_rejects_automatic_trust_in_sources():
    """General conversation must not treat neutrality as automatic trust in any source class."""
    import inspect
    import tasks.telegram_bot as telegram_bot_module

    import unicodedata

    source = inspect.getsource(telegram_bot_module.TelegramBot)
    normalized = "".join(
        char for char in unicodedata.normalize("NFD", source.casefold())
        if unicodedata.category(char) != "Mn"
    )
    assert "nao confunda neutralidade com confiar automaticamente em fontes oficiais" in normalized
    assert "reputacao e alinhamento politico nao provam nem refutam" in normalized


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeHTTP:
    def __init__(self):
        self.calls = []

    def post(self, url, json=None, data=None, files=None, timeout=None):
        self.calls.append(("POST", url, json, data, files))
        if "127.0.0.1:11434/api/generate" in url:
            prompt = (json or {}).get("prompt", "")
            if "Classifique a mensagem" in prompt:
                answer = getattr(self, "intent_response", "CHAT")
                if answer == "AUTO":
                    answer = "ACAO" if "abra" in prompt.lower() or "pesquise" in prompt.lower() else "CHAT"
                return FakeResponse({"response": answer})
            return FakeResponse({"response": "Python é uma linguagem de programação."})
        if "/sendPhoto" in url:
            return FakeResponse({"ok": True, "result": {"message_id": 2}})
        return FakeResponse({"ok": True, "result": {"message_id": 1}})

    def get(self, url, params=None, timeout=None):
        self.calls.append(("GET", url, params, None, None))
        if url.endswith("/api/tags"):
            return FakeResponse({"models": [
                {"name": "qwen2.5:3b-instruct-q5_K_M", "size": 3000000000},
                {"name": "llama3.2:3b", "size": 2000000000},
            ]})
        return FakeResponse({"ok": True, "result": []})

    def request(self, method, url, json=None, timeout=None):
        self.calls.append((method, url, json, None, None))
        if url.endswith("/task_status"):
            return FakeResponse({"state": "idle", "objetivo": None, "passo_atual": None})
        if url.endswith("/task_simple"):
            return FakeResponse({"status": "ok", "resultado_final": "Tarefa concluida"})
        if url.endswith("/pc_screenshot"):
            return FakeResponse({"status": "ok", "path": self.screenshot_path})
        if url.endswith("/see"):
            return FakeResponse({"status": "ok", "result": "A tela mostra uma janela."})
        return FakeResponse({"status": "ok", "result": "OK"})


def update(chat_id, text):
    return {
        "update_id": 7,
        "message": {"chat": {"id": chat_id}, "text": text},
    }


def test_bot_requires_token_and_allowlist():
    bot = TelegramBot(token="", allowed_chat_ids=set())
    result = bot.start()
    assert result["status"] == "erro"
    assert bot.status()["running"] is False


def test_unauthorized_chat_is_ignored():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    bot.handle_update(update(999, "/help"))
    assert http.calls == []


def test_help_and_status_are_available_to_allowed_chat():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    bot.handle_update(update(123, "/help"))
    bot.handle_update(update(123, "/status"))
    sent = [call for call in http.calls if "/sendMessage" in call[1]]
    assert len(sent) == 2
    assert "/task" in sent[0][2]["text"]
    assert "Estado: idle" in sent[1][2]["text"]


def test_task_command_rejects_empty_and_overlong_objectives():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    bot.handle_update(update(123, "/task"))
    bot.handle_update(update(123, "/task " + ("x" * 1201)))
    sent = [call for call in http.calls if "/sendMessage" in call[1]]
    assert len(sent) == 2
    assert "Uso: /task" in sent[0][2]["text"]
    assert "muito longo" in sent[1][2]["text"]
    assert not any(call[1].endswith("/task_simple") for call in http.calls)


def test_screenshot_is_sent_only_on_explicit_command(tmp_path):
    screenshot = tmp_path / "screen.png"
    screenshot.write_bytes(b"fake-png")
    http = FakeHTTP()
    http.screenshot_path = str(screenshot)
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    bot.handle_update(update(123, "/screenshot"))
    photos = [call for call in http.calls if "/sendPhoto" in call[1]]
    assert len(photos) == 1
    assert photos[0][4]["photo"][0] == "screen.png"


def test_natural_language_screenshot_request_sends_photo(tmp_path):
    screenshot = tmp_path / "screen.png"
    screenshot.write_bytes(b"fake-png")
    http = FakeHTTP()
    http.screenshot_path = str(screenshot)
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)

    bot._route_text_message("123", "mande um imagem da tela do meu compuatdor")

    photos = [call for call in http.calls if "/sendPhoto" in call[1]]
    assert len(photos) == 1
    assert photos[0][4]["photo"][0] == "screen.png"
    assert not any("11434/api/generate" in call[1] for call in http.calls)


def test_see_command_returns_visual_summary():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    bot.handle_update(update(123, "/see o que aparece?"))
    sent = [call for call in http.calls if "/sendMessage" in call[1]]
    assert "A tela mostra uma janela." in sent[-1][2]["text"]


def test_natural_screen_question_uses_real_vision_endpoint():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    bot._route_text_message("123", "O que você vê na minha tela")
    assert any(call[0] == "POST" and call[1].endswith("/see") for call in http.calls)
    assert not any("11434/api/generate" in call[1] for call in http.calls)
    sent = [call for call in http.calls if "/sendMessage" in call[1]]
    assert "A tela mostra uma janela." in sent[-1][2]["text"]


def test_cancel_and_pause_call_only_local_agent_routes():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    bot.handle_update(update(123, "/cancel"))
    bot.handle_update(update(123, "/pause"))
    routes = [call[1] for call in http.calls if call[0] == "POST" and "127.0.0.1:8000" in call[1]]
    assert any(route.endswith("/task_cancel") for route in routes)
    assert any(route.endswith("/task_pause") for route in routes)


def test_visual_followups_about_other_tabs_keep_using_screen_analysis():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)

    bot._route_text_message("123", "o que voce ve na tela")
    bot._route_text_message("123", "me de detalhes de outras abas")
    bot._route_text_message("123", "e me de mais detalhes")

    see_calls = [call for call in http.calls if call[1].endswith("/see")]
    assert len(see_calls) == 3
    assert see_calls[1][2] == {"pergunta": "me de detalhes de outras abas"}
    assert see_calls[2][2] == {"pergunta": "e me de mais detalhes"}
    assert not any("127.0.0.1:11434/api/generate" in call[1] for call in http.calls)


def test_plain_text_is_routed_without_command_prefix():
    import threading

    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    received = []
    done = threading.Event()

    def route(chat_id, text):
        received.append((chat_id, text))
        done.set()

    bot._route_text_message = route
    bot.handle_update(update(123, "Quem é você?"))
    assert done.wait(1)
    assert received == [("123", "Quem é você?")]
    assert not any(call[1].endswith("/task_simple") for call in http.calls)


def test_free_text_chat_uses_local_ollama_and_sends_answer():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)

    bot._route_text_message("123", "O que é Python?")

    sent = [call for call in http.calls if "/sendMessage" in call[1]]
    assert "Python é uma linguagem de programação." in sent[-1][2]["text"]
    assert any("127.0.0.1:11434/api/generate" in call[1] for call in http.calls)
    assert not any(call[1].endswith("/task_simple") for call in http.calls)


def test_chat_keeps_recent_context_per_chat():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)

    bot._chat("Meu nome é Gabriel.", chat_id="123")
    bot._chat("Qual é o meu nome?", chat_id="123")
    bot._chat("Qual é o meu nome?", chat_id="456")

    calls = [call for call in http.calls if "127.0.0.1:11434/api/generate" in call[1]]
    assert "Usuário: Meu nome é Gabriel." in calls[1][2]["prompt"]
    assert "Usuário: Qual é o meu nome?" in calls[1][2]["prompt"]
    assert "Meu nome é Gabriel." not in calls[2][2]["prompt"]


def test_open_google_routes_directly_not_through_generic_task():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    routed = []
    bot._start_routed_task = lambda chat_id, objective: routed.append((chat_id, objective))

    bot._route_text_message("123", "Abra o Google")

    opened = [call for call in http.calls if call[1].endswith("/open_url")]
    assert len(opened) == 1
    assert opened[0][2] == {"url": "https://www.google.com"}
    assert routed == []
    assert not any("127.0.0.1:11434/api/generate" in call[1] for call in http.calls)


def test_information_question_never_routes_to_computer_even_if_classifier_would():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    routed = []
    bot._start_routed_task = lambda chat_id, objective: routed.append((chat_id, objective))
    bot._classify_intent = lambda text: "ACAO"

    bot._route_text_message("123", "Como plantar tomates em vasos?")

    sent = [call for call in http.calls if "/sendMessage" in call[1]]
    assert "Python é uma linguagem de programação." in sent[-1][2]["text"]
    assert routed == []
    assert not any(call[1].endswith("/task_simple") for call in http.calls)


def test_explicit_web_search_command_routes_to_computer():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    routed = []
    bot._start_routed_task = lambda chat_id, objective: routed.append((chat_id, objective))

    bot._route_text_message("123", "Pesquise na web como plantar tomates")

    assert routed == [("123", "Pesquise na web como plantar tomates")]


def test_contextualized_desktop_command_routes_to_task_not_chat():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    routed = []
    bot._start_routed_task = lambda chat_id, objective: routed.append((chat_id, objective))
    objective = (
        "No Notepad, clique no menu View e verifique visualmente se o menu foi aberto. "
        "Não execute nenhuma outra ação."
    )

    assert TelegramBot._is_explicit_computer_action(objective)
    bot._route_text_message("123", objective)

    assert routed == [("123", objective)]
    assert not any("11434/api/generate" in call[1] for call in http.calls)


def test_uncertain_intent_defaults_to_chat_not_computer_action():
    http = FakeHTTP()
    http.intent_response = "nao sei"
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)

    assert bot._classify_intent("talvez faça algo") == "CHAT"


def test_models_command_lists_local_models_and_current_selection():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    bot.chat_model = "qwen2.5:3b-instruct-q5_K_M"
    bot.handle_update(update(123, "/models"))
    sent = [call for call in http.calls if "/sendMessage" in call[1]]
    assert "llama3.2:3b" in sent[-1][2]["text"]
    assert bot.chat_model in sent[-1][2]["text"]
    keyboard = sent[-1][2]["reply_markup"]["inline_keyboard"]
    assert any(button["callback_data"] == "model:llama3.2:3b" for row in keyboard for button in row)


def test_model_button_changes_only_telegram_chat_model(monkeypatch, tmp_path):
    import tasks.telegram_bot as telegram_module

    state_file = tmp_path / ".telegram_chat_model"
    monkeypatch.setattr(telegram_module, "CHAT_MODEL_STATE_FILE", state_file)
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    bot.handle_update({
        "update_id": 8,
        "callback_query": {
            "id": "callback-1",
            "data": "model:llama3.2:3b",
            "message": {"chat": {"id": 123}},
        },
    })

    assert bot.chat_model == "llama3.2:3b"
    assert state_file.read_text(encoding="utf-8") == "llama3.2:3b"
    assert any("/answerCallbackQuery" in call[1] for call in http.calls)
    sent = [call for call in http.calls if "/sendMessage" in call[1]]
    assert "A MYRA principal não foi alterada" in sent[-1][2]["text"]


def test_model_command_changes_only_telegram_chat_model(monkeypatch, tmp_path):
    import tasks.telegram_bot as telegram_module

    state_file = tmp_path / ".telegram_chat_model"
    monkeypatch.setattr(telegram_module, "CHAT_MODEL_STATE_FILE", state_file)
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    original = bot.chat_model

    bot.handle_update(update(123, "/model llama3.2:3b"))

    assert bot.chat_model == "llama3.2:3b"
    assert state_file.read_text(encoding="utf-8") == "llama3.2:3b"
    assert original != bot.chat_model
    sent = [call for call in http.calls if "/sendMessage" in call[1]]
    assert "A MYRA principal não foi alterada" in sent[-1][2]["text"]


def test_chat_falls_back_if_selected_model_fails(monkeypatch, tmp_path):
    import tasks.telegram_bot as telegram_module

    monkeypatch.setattr(telegram_module, "CHAT_MODEL_STATE_FILE", tmp_path / ".telegram_chat_model")
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    bot.chat_model = "model-that-fails"
    calls = []

    def generate(prompt, **kwargs):
        calls.append(kwargs.get("model"))
        if kwargs.get("model") == "model-that-fails":
            raise RuntimeError("model failed to load")
        return "Resposta de contingência."

    bot._ollama_generate = generate
    answer = bot._chat("Oi", chat_id="123")

    assert calls == ["model-that-fails", telegram_module.DEFAULT_CHAT_MODEL]
    assert "Usei temporariamente o modelo" in answer
    assert "Resposta de contingência." in answer


def test_chat_uses_selected_model_but_classifier_keeps_default(monkeypatch, tmp_path):
    import tasks.telegram_bot as telegram_module

    monkeypatch.setattr(telegram_module, "CHAT_MODEL_STATE_FILE", tmp_path / ".telegram_chat_model")
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    bot.chat_model = "llama3.2:3b"

    assert bot._chat("Oi") == "Python é uma linguagem de programação."
    generate_calls = [call for call in http.calls if "127.0.0.1:11434/api/generate" in call[1]]
    assert generate_calls[-1][2]["model"] == "llama3.2:3b"

    bot._classify_intent("Quem é você?")
    generate_calls = [call for call in http.calls if "127.0.0.1:11434/api/generate" in call[1]]
    assert generate_calls[-1][2]["model"] == telegram_module.DEFAULT_CHAT_MODEL


def test_model_command_rejects_uninstalled_model():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    original = bot.chat_model
    bot.handle_update(update(123, "/model modelo-inexistente"))
    assert bot.chat_model == original
    sent = [call for call in http.calls if "/sendMessage" in call[1]]
    assert "não está instalado" in sent[-1][2]["text"]


def test_commands_alias_and_ping():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    bot.handle_update(update(123, "/commands"))
    bot.handle_update(update(123, "/ping"))
    sent = [call for call in http.calls if "/sendMessage" in call[1]]
    assert "/models" in sent[0][2]["text"]
    assert "/taskinfo" in sent[0][2]["text"]
    assert "MYRA backend: online" in sent[1][2]["text"]


def test_task_command_still_bypasses_intent_router():
    import threading

    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    done = threading.Event()
    called = []
    bot._classify_intent = lambda text: called.append(("classified", text)) or "CHAT"

    def run_task(chat_id, objective):
        called.append((chat_id, objective))
        done.set()

    bot._run_task = run_task
    bot.handle_update(update(123, "/task abra o Google"))

    assert done.wait(1)
    assert called == [("123", "abra o Google")]
    assert not any("127.0.0.1:11434/api/generate" in call[1] for call in http.calls)


def test_task_result_and_followup_context_persist_across_restart(monkeypatch, tmp_path):
    import tasks.telegram_bot as telegram_module

    memory_file = tmp_path / ".telegram_chat_memory.json"
    monkeypatch.setattr(telegram_module, "CHAT_MEMORY_FILE", memory_file)
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)

    bot._remember_chat_turn("123", "user", "Pesquise como plantar tomates")
    bot._run_task("123", "Pesquise como plantar tomates")

    # Simula reiniciar o bot/backend: o contexto deve voltar do arquivo local.
    restarted_bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    assert "Pesquise como plantar tomates" in str(restarted_bot._chat_history["123"])
    assert "Tarefa concluida" in str(restarted_bot._chat_history["123"])

    restarted_bot._chat("Quero um passo a passo", chat_id="123")
    generate_calls = [
        call for call in http.calls
        if "127.0.0.1:11434/api/generate" in call[1]
    ]
    prompt = generate_calls[-1][2]["prompt"]
    assert "Pesquise como plantar tomates" in prompt
    assert "Tarefa concluida" in prompt
    assert "Quero um passo a passo" in prompt


def test_open_google_uses_direct_open_url_not_search_or_generic_task():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    routed = []
    bot._start_routed_task = lambda chat_id, objective: routed.append((chat_id, objective))

    bot._route_text_message("123", "Abra o Google")

    opened = [call for call in http.calls if call[1].endswith("/open_url")]
    assert len(opened) == 1
    assert opened[0][2] == {"url": "https://www.google.com"}
    assert routed == []
    assert not any(call[1].endswith("/search_google") or call[1].endswith("/task_simple") for call in http.calls)


def test_direct_open_application_target_resolves_windows_aliases():
    assert TelegramBot._direct_open_application_target("Abra os meus arquivos") == "explorador de arquivos"
    assert TelegramBot._direct_open_application_target("Abra o Chrome") == "chrome"
    assert TelegramBot._direct_open_application_target("Abra o Google") is None
    assert TelegramBot._direct_open_application_target("Sim, pode abrir o Bloco de Notas.") == "bloco de notas"
    assert TelegramBot._direct_open_application_target("Pode abrir o Bloco de Notas.") == "bloco de notas"


def test_open_local_application_uses_safe_application_endpoint():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    routed = []
    bot._start_routed_task = lambda chat_id, objective: routed.append((chat_id, objective))

    bot._route_text_message("123", "Abra os meus arquivos")
    bot._route_text_message("123", "Abra o Chrome")

    opened = [call for call in http.calls if call[1].endswith("/pc_open_application")]
    assert [call[2] for call in opened] == [
        {"nome": "explorador de arquivos"},
        {"nome": "chrome"},
    ]
    assert routed == []
    assert not any(call[1].endswith("/task_simple") for call in http.calls)


def test_election_question_is_routed_to_web_search_not_local_chat():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    web_questions = []
    bot._handle_web_question = lambda chat_id, text: web_questions.append((chat_id, text))

    question = "Qual foi o resultado das elei\\u00e7\\u00f5es?"
    bot._route_text_message("123", question)

    assert web_questions == [("123", question)]
    assert not any("127.0.0.1:11434/api/generate" in call[1] for call in http.calls)


def test_voting_advice_is_routed_to_neutral_web_research():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    web_questions = []
    bot._handle_web_question = lambda chat_id, text: web_questions.append((chat_id, text))

    question = "Em que voce aconselha votar?"
    bot._route_text_message("123", question)

    assert web_questions == [("123", question)]
    assert not any("127.0.0.1:11434/api/generate" in call[1] for call in http.calls)


def test_generic_research_intent_is_routed_to_web():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    web_questions = []
    bot._handle_web_question = lambda chat_id, text: web_questions.append((chat_id, text))

    question = "Pesquise fontes confiaveis sobre energia solar"
    bot._route_text_message("123", question)

    assert web_questions == [("123", question)]



def test_long_internet_research_request_is_not_misrouted_to_operational_status():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    web_questions = []
    bot._handle_web_question = lambda chat_id, text: web_questions.append((chat_id, text))

    question = (
        "Pesquise na internet informa??es atualizadas sobre os avan?os da intelig?ncia artificial "
        "e da rob?tica em 2026. Encontre pelo menos 5 not?cias recentes de fontes confi?veis, "
        "como Reuters, BBC, TechCrunch ou ve?culos especializados. Para cada resultado, apresente "
        "o t?tulo, um resumo dos principais fatos, a data da publica??o, o nome da fonte e o link "
        "direto para a not?cia. N?o invente informa??es nem links. Se algum provedor de pesquisa "
        "falhar, tente os outros dispon?veis antes de responder. No final, informe quantos "
        "resultados foram encontrados e quais fontes foram consultadas."
    )
    bot._route_text_message("123", question)

    assert web_questions == [("123", question)]
    assert not any(call[1].endswith("/telegram/status") for call in http.calls)

def test_exact_myra_critical_investigation_brief_routes_to_web_not_status():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    web_questions = []
    bot._handle_web_question = lambda chat_id, text: web_questions.append((chat_id, text))

    question = (
        "MYRA, quero que voce faca uma investigacao critica e imparcial sobre a seguinte questao: "
        "O governo brasileiro e o STF agiram dentro dos limites legais e constitucionais nos "
        "processos relacionados aos acontecimentos de 8 de janeiro de 2023? Consulte fontes de "
        "diferentes perspectivas, verifique documentos originais, analise competencia do tribunal, "
        "imparcialidade, decisoes monocraticas, direito de defesa, individualizacao das condutas, "
        "proporcionalidade das penas e aplicacao dos crimes. Para cada critica, identifique evidencias, "
        "argumentos contrarios e o que a legislacao permite concluir. Diferencie fatos comprovados, "
        "alegacoes, interpretacoes juridicas e opinioes politicas. Apresente resumo, argumentos a favor "
        "e contra, analise de cada controversia, fontes com links diretos, limitacoes e conclusao final. "
        "Nao presuma que o STF agiu corretamente por ser oficial nem que agiu ilegalmente porque recebeu "
        "criticas. Avalie cada afirmacao com base nas evidencias e diga explicitamente quando nao houver "
        "base suficiente para uma conclusao segura."
    )
    assert len(question) >= 700

    bot._route_text_message("123", question)

    assert web_questions == [("123", question)]
    assert not any(call[1].endswith("/telegram/status") for call in http.calls)


def test_plain_factual_questions_are_routed_to_web_without_research_keyword():
    assert TelegramBot._is_current_web_question("Quem inventou a internet?")
    assert TelegramBot._is_current_web_question("Qual a diferenca entre energia solar e eolica?")
    assert TelegramBot._is_current_web_question("How does a heat pump work?")
    assert not TelegramBot._is_current_web_question("Abra o Chrome")


def test_voting_research_query_is_neutral_and_source_oriented():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    requests = []
    prompts = []
    bot._agent_request = lambda method, route, payload=None, timeout=20: (
        requests.append((method, route, payload, timeout)) or
        {"status": "ok", "result": "Fontes eleitorais com propostas e programas oficiais. URL: https://example.org"}
    )
    bot._ollama_generate = lambda prompt, **kwargs: prompts.append(prompt) or "Compare as propostas de forma equilibrada. https://example.org"

    bot._handle_web_question("123", "Em que voce aconselha votar?")

    assert len(requests) == 1
    assert "comparar propostas" in requests[0][2]["query"]
    assert "nao escolha um candidato nem tente persuadir" in prompts[0]
    assert "evidencias web fornecidas" in prompts[0]


def test_allegation_about_election_turn_keeps_claim_in_web_search_query():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    requests = []
    bot._agent_request = lambda method, route, payload=None, timeout=20: (
        requests.append((method, route, payload, timeout)) or
        {"status": "ok", "result": "TSE e agências de checagem publicaram documentos. URL: https://example.org"}
    )
    bot._ollama_generate = lambda prompt, **kwargs: "As fontes precisam ser verificadas. https://example.org"

    question = "Procure evidências de um golpe no segundo turno das eleições por parte do PT"
    bot._handle_web_question("123", question)

    assert len(requests) == 3
    queries = [request[2]["query"] for request in requests]
    assert all(question in query for query in queries)
    assert any("TSE" in query and "decisões judiciais" in query for query in queries)
    assert any("checagem de fatos" in query for query in queries)
    assert any("jornalismo" in query and "independentes" in query for query in queries)
    sent = [call[2]["text"] for call in http.calls if "/sendMessage" in call[1]]
    assert any("As fontes precisam ser verificadas" in message for message in sent)



def test_long_investigation_prompt_is_trimmed_to_actual_question():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    requests = []
    bot._agent_request = lambda method, route, payload=None, timeout=20: (
        requests.append((method, route, payload, timeout)) or
        {"status": "ok", "result": "Documento oficial e checagem independente. URL: https://example.org"}
    )
    bot._ollama_generate = lambda prompt, **kwargs: "As fontes precisam ser verificadas. https://example.org"
    question = (
        "Quero que voce faca uma investigacao imparcial sobre a seguinte questao:\n\n"
        "Existem evidencias de fraude no segundo turno das eleicoes presidenciais brasileiras de 2022 atribuida ao PT?\n\n"
        "Siga estas instrucoes:\n\n1. Faca pelo menos 3 pesquisas na web.\n"
        "2. Consulte fontes oficiais e checagem independente.\nFormato da resposta: resumo e fontes."
    )

    bot._handle_web_question("123", question)

    queries = [request[2]["query"] for request in requests]
    assert len(queries) == 3
    assert all("Existem evidencias de fraude no segundo turno" in query for query in queries)
    assert all("Siga estas instrucoes" not in query for query in queries)
    assert all("Formato da resposta" not in query for query in queries)

def test_short_followup_reuses_only_the_investigation_topic_not_full_briefing():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    requests = []
    prompts = []
    bot._agent_request = lambda method, route, payload=None, timeout=20: (
        requests.append((method, route, payload, timeout)) or
        {"status": "ok", "result": "Relatorio e fontes sobre Covaxin. URL: https://example.org"}
    )
    bot._ollama_generate = lambda prompt, **kwargs: prompts.append(prompt) or "As fontes precisam ser verificadas. https://example.org"
    initial = (
        "MYRA, faça uma investigação jornalística sobre o caso Covaxin no Brasil, relacionado às negociações "
        "para aquisição da vacina contra a COVID-19 em 2021.\n\nSiga estas instruções:\n"
        "1. Pesquise fontes primárias.\n2. Identifique responsáveis e conclusões.\n"
        "3. Apresente uma cronologia e links diretos."
    )
    bot._remember_chat_turn("123", "user", initial)

    bot._handle_web_question("123", "Quem é o principal apontado?")

    queries = [request[2]["query"] for request in requests]
    assert len(queries) == 3
    assert all("Covaxin no Brasil" in query for query in queries)
    assert all("Quem é o principal apontado?" in query for query in queries)
    assert all("Siga estas instruções" not in query for query in queries)
    assert all("cronologia e links diretos" not in query for query in queries)
    assert "Contexto da investigação/pergunta completa: o caso Covaxin no Brasil" in prompts[0]


def test_web_search_failure_sends_progress_and_explicit_error():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    requests = []

    def failed_search(method, route, payload=None, timeout=20):
        requests.append((method, route, payload, timeout))
        return {"status": "erro", "result": "network down"}

    bot._agent_request = failed_search
    bot._handle_web_question("123", "Qual foi o resultado das eleicoes?")

    assert requests and requests[0][0:2] == ("POST", "/web_search")
    assert requests[0][2]["max_resultados"] == 5
    sent = [call[2]["text"] for call in http.calls if "/sendMessage" in call[1]]
    assert any("Vou pesquisar na web" in message for message in sent)
    assert any("Nao consegui confirmar" in message for message in sent)


def test_brazil_election_search_uses_final_results_query_and_more_sources():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    requests = []
    bot._agent_request = lambda method, route, payload=None, timeout=20: (
        requests.append((method, route, payload, timeout)) or
        {"status": "ok", "result": "TSE: candidato eleito com votos e percentual. URL: https://tse.jus.br/resultado"}
    )
    bot._ollama_generate = lambda prompt, **kwargs: "Resultado confirmado com dados. https://tse.jus.br/resultado"

    bot._handle_web_question("123", "Qual foi o resultado das eleições no Brasil")

    assert requests[0][2]["max_resultados"] == 5
    assert "resultado final" in requests[0][2]["query"]
    assert "TSE" in requests[0][2]["query"]
    sent = [call[2]["text"] for call in http.calls if "/sendMessage" in call[1]]
    assert any("Resultado confirmado" in message for message in sent)


def test_allegation_research_never_uses_2026_winner_shortcut():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    requests = []
    bot._agent_request = lambda method, route, payload=None, timeout=20: (
        requests.append((method, route, payload, timeout)) or
        {"status": "ok", "result": "TSE, checagem independente e reportagem: evidências precisam ser avaliadas. URL: https://example.org"}
    )
    prompts = []
    bot._ollama_generate = lambda prompt, **kwargs: prompts.append(prompt) or (
        "As fontes disponíveis não comprovam a alegação; seria necessário analisar os documentos citados. https://example.org"
    )
    question = (
        "Quero uma investigação imparcial: existem evidências de fraude, irregularidades ou "
        "manipulação no segundo turno das eleições presidenciais brasileiras de 2022 que possam ser atribuídas ao PT?"
    )

    bot._handle_web_question("123", question)

    assert len(requests) == 3
    assert all(question in request[2]["query"] for request in requests)
    assert len(prompts) == 1
    sent = [call[2]["text"] for call in http.calls if "/sendMessage" in call[1]]
    assert any("não comprovam a alegação" in message for message in sent)
    assert not any("64.256.232" in message or "51,79%" in message for message in sent)


def test_brazil_2026_election_answer_must_come_from_model_and_search_sources():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    bot._agent_request = lambda *args, **kwargs: {
        "status": "ok",
        "result": (
            "[1] Resultado eleitoral - fonte jornalistica\n"
            "URL: https://example.org/eleicoes\n"
            "A fonte afirma que a apuracao foi concluida, mas precisa ser verificada."
        ),
    }
    model_calls = []
    bot._ollama_generate = lambda *args, **kwargs: model_calls.append(args) or (
        "Nao consigo confirmar o vencedor com os dados fornecidos."
    )

    bot._handle_web_question("123", "Quem ganhou as eleicoes do Brasil?")

    sent = [call[2]["text"] for call in http.calls if "/sendMessage" in call[1]]
    answer = sent[-1]
    assert "Nao consigo confirmar o vencedor" in answer
    assert "https://example.org/eleicoes" in answer
    assert model_calls, "A resposta deve ser gerada a partir das fontes, nao de um resultado pre-fabricado"
    assert "64.256.232" not in answer
    assert "Luiz In\u00e1cio Lula da Silva" not in answer


def test_web_answer_prompt_requires_numbers_and_rejects_false_no_result_claims():
    import inspect
    import tasks.telegram_bot as telegram_bot_module

    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    prompts = []
    bot._agent_request = lambda *args, **kwargs: {"status": "ok", "result": "TSE informa candidato eleito, votos e percentual. URL: https://tse.jus.br/resultado"}
    bot._ollama_generate = lambda prompt, **kwargs: (prompts.append(prompt) or "Resposta direta. https://tse.jus.br/resultado")

    bot._handle_web_question("123", "Qual foi o resultado das eleições no Brasil")

    assert "nunca conclua que nao existe resultado final" in prompts[0]
    assert "apresente nome, votos, percentual" in prompts[0]
    assert "Use somente fatos e URLs que aparecam nos resultados fornecidos" in prompts[0]
    assert "noticias de outra eleicao/ano nao constituem evidencia" in prompts[0]
    assert "responda a cada secao" in prompts[0]
    assert "PROTOCOLO DE RACIOCINIO ANALITICO OBRIGATORIO" in prompts[0]
    assert "VALIDACAO DE CONSISTENCIA OBRIGATORIA" in prompts[0]
    import unicodedata
    normalized_prompt = "".join(
        char for char in unicodedata.normalize("NFD", prompts[0].casefold())
        if unicodedata.category(char) != "Mn"
    )
    assert "a conclusao deve ser uma avaliacao propria" in normalized_prompt
    source = inspect.getsource(telegram_bot_module.TelegramBot._handle_web_question)
    assert "_filter_jan8_stf_sources(batch_text)" in source
    assert "Alternativa descartada por irrelevância temática" in source
    assert "jan8_stf = bool(" in source


def test_start_blocks_second_process_polling_lock():
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"})
    bot._acquire_polling_lock = lambda: False

    result = bot.start()

    assert result["status"] == "erro"
    assert "outro processo" in result["result"]
    assert bot.status()["running"] is False


def test_guarded_message_router_reports_unexpected_errors():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    bot._route_text_message = lambda chat_id, text: (_ for _ in ()).throw(RuntimeError("boom"))

    bot._route_text_message_guarded("123", "mensagem")

    sent = [call[2]["text"] for call in http.calls if "/sendMessage" in call[1]]
    assert any("falha interna" in message for message in sent)
    assert bot.status()["last_error"] == "route_message: RuntimeError"


def test_direct_open_target_resolves_common_sites():
    assert TelegramBot._direct_open_target("Abra o Google") == "https://www.google.com"
    assert TelegramBot._direct_open_target("Abra o YouTube") == "https://www.youtube.com"
    assert TelegramBot._direct_open_target("Open GitHub") == "https://github.com"
    assert TelegramBot._direct_open_target("Pesquise no Google por tomates") is None


def test_poll_loop_stops_after_telegram_409_conflict():
    import requests
    from unittest.mock import Mock

    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"})
    response = Mock(status_code=409)
    response.json.return_value = {
        "ok": False,
        "description": "Conflict: terminated by other getUpdates request",
    }
    error = requests.exceptions.HTTPError(response=response)

    def conflict(*args, **kwargs):
        raise error

    bot._telegram = conflict
    bot._poll_loop()

    assert bot._stop_event.is_set()
    assert bot.status()["running"] is False
    assert "409 Conflict" in bot.status()["last_error"]
    assert "another getUpdates poller" in bot.status()["last_error"]


def test_start_refuses_to_create_second_thread_while_previous_thread_exits():
    from unittest.mock import Mock

    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"})
    old_thread = Mock()
    old_thread.is_alive.return_value = True
    bot._thread = old_thread
    bot._stop_event.set()

    result = bot.start()

    assert result["status"] == "erro"
    assert "ainda esta encerrando" in result["result"]
    assert bot._thread is old_thread


def test_successful_poll_clears_stale_transient_error():
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"})
    bot._last_error = "polling: ReadTimeout"

    def recovered_poll(*args, **kwargs):
        bot._stop_event.set()
        return {"result": []}

    bot._telegram = recovered_poll
    bot._poll_loop()

    assert bot.status()["last_error"] is None
    assert bot.status()["running"] is False


def test_long_responses_are_sent_in_chunks_without_truncation():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    original = ("Parágrafo completo com conteúdo importante. " * 220).strip()

    assert bot._send_message("123", original)
    sent = [call[2]["text"] for call in http.calls if "/sendMessage" in call[1]]

    assert len(sent) > 1
    assert all(0 < len(chunk) <= 3900 for chunk in sent)
    assert "".join(sent) == original


def test_short_result_does_not_truncate_long_agent_response():
    original = "x" * 12000
    assert TelegramBot._short_result({"status": "ok", "result": original}) == original


def test_visual_followup_requests_fresh_screen_analysis():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)

    bot.handle_update(update(123, "/see"))
    bot._route_text_message("123", "me de mais detalhes")

    see_calls = [call for call in http.calls if call[1].endswith("/see")]
    assert len(see_calls) == 2
    assert see_calls[1][2]["pergunta"] == "me de mais detalhes"
    history = bot._chat_history["123"]
    assert history[-2]["content"] == "me de mais detalhes"
    assert history[-1]["content"] == "A tela mostra uma janela."

def test_natural_screenshot_request_does_not_claim_success_when_photo_upload_fails(tmp_path):
    screenshot = tmp_path / "screen.png"
    screenshot.write_bytes(b"fake-png")
    http = FakeHTTP()
    http.screenshot_path = str(screenshot)
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    original_telegram = bot._telegram

    def fail_photo_upload(method, **kwargs):
        if method == "sendPhoto":
            raise RuntimeError("simulated Telegram upload failure")
        return original_telegram(method, **kwargs)

    bot._telegram = fail_photo_upload
    bot._route_text_message("123", "Mande uma imagem da tela do meu computador")

    assert "upload failure" in (bot.status()["last_error"] or "")
    assert not any(
        turn["content"] == "Captura da tela enviada pelo Telegram."
        for turn in bot._chat_history.get("123", [])
    )
    sent = [call for call in http.calls if "/sendMessage" in call[1]]
    assert any("Falha ao capturar/enviar a tela" in call[2]["text"] for call in sent)


def test_long_research_prompt_is_reduced_to_its_core_topic():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    requests = []
    bot._agent_request = lambda method, route, payload=None, timeout=20: (
        requests.append((method, route, payload, timeout)) or
        {"status": "ok", "result": "Avanços recentes em IA e robótica. URL: https://example.org"}
    )
    bot._ollama_generate = lambda prompt, **kwargs: "Resumo baseado nos resultados. https://example.org"
    bot._send_message = lambda chat_id, text: None
    bot._remember_chat_turn = lambda chat_id, role, content: None

    question = (
        "Pesquise na internet informações atualizadas sobre os avanços da inteligência artificial "
        "e da robótica em 2026. Encontre pelo menos 5 notícias recentes de fontes confiáveis, "
        "como Reuters, BBC, TechCrunch ou veículos especializados. Para cada resultado, apresente "
        "o título, um resumo dos principais fatos, a data da publicação, o nome da fonte e o link "
        "direto para a notícia. Não invente informações nem links. Se algum provedor de pesquisa "
        "falhar, tente os outros disponíveis antes de responder. No final, informe quantos resultados "
        "foram encontrados e quais fontes foram consultadas."
    )

    bot._handle_web_question("123", question)

    assert requests
    assert len(requests[0][2]["query"]) < 100
    assert "inteligência artificial" in requests[0][2]["query"]
    assert "Reuters" not in requests[0][2]["query"]



def test_weather_router_extracts_city_from_actual_forecast_request():
    assert TelegramBot._extract_weather_city(
        "Qual o forecast do tempo em Roscommon Irlanda pela próxima semana"
    ) == "Roscommon Irlanda"


def test_weather_router_ignores_incidental_weather_mention_in_long_diagnostic():
    diagnostic = (
        "MYRA, interrompa a resposta meteorológica e retome a tarefa de diagnóstico e correção "
        "do pipeline de pesquisa que solicitei anteriormente. Não execute uma nova consulta sobre "
        "o clima. Não responda novamente à investigação jurídica antes de verificar o problema técnico. "
        "Identifique os arquivos responsáveis, examine os logs e corrija a causa raiz."
    )
    assert TelegramBot._extract_weather_city(diagnostic) is None


def test_weather_router_ignores_explicit_negative_weather_instruction():
    assert TelegramBot._extract_weather_city(
        "Não execute uma nova consulta sobre o clima."
    ) is None


def test_long_diagnostic_routes_to_task_not_weather():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    routes = []
    bot._agent_request = lambda method, route, payload=None, timeout=20: (
        routes.append((method, route, payload)) or {"status": "ok", "result": "OK"}
    )
    bot._handle_web_question = lambda chat_id, text: routes.append(("RESEARCH", chat_id, text))
    bot._start_routed_task = lambda chat_id, objective: routes.append(("TASK", chat_id, objective))
    bot._send_message = lambda chat_id, text: None
    bot._remember_chat_turn = lambda chat_id, role, content: None

    diagnostic = (
        "MYRA, interrompa a resposta meteorológica e retome a tarefa de diagnóstico e correção "
        "do pipeline de pesquisa que solicitei anteriormente. Não execute uma nova consulta sobre "
        "o clima. Não responda novamente à investigação jurídica antes de verificar o problema técnico. "
        "Identifique os arquivos responsáveis, examine os logs e corrija a causa raiz."
    )
    diagnostic += " " + ("detalhe operacional " * 100)
    bot._route_text_message("123", diagnostic)

    task_calls = [item for item in routes if item[0] == "TASK"]
    assert task_calls
    assert len(task_calls[0][2]) <= 1200
    assert "Diagnostique e corrija" in task_calls[0][2]
    assert not any(item[1] == "/get_weather" for item in routes if len(item) > 1)



def test_jan8_stf_filter_discards_irrelevant_items_inside_relevant_batch():
    batch = (
        "[1] Entenda as condenações de réus pelos atos antidemocráticos de 8 de janeiro\n"
        "    URL: https://portal.stf.jus.br/noticias/verNoticiaDetalhe.asp?idConteudo=517059\n"
        "    O Plenário do Supremo Tribunal Federal iniciou o julgamento das ações penais.\n\n"
        "[2] Projeto define regras para participação de filhos em atividades rurais\n"
        "    URL: https://www.camara.leg.br/noticias/1314150-projeto-rural\n"
        "    Projeto de lei sobre atividades práticas e gestão da propriedade familiar.\n\n"
        "[3] Projeto prevê GPS obrigatório em veículos de transporte escolar\n"
        "    URL: https://www.camara.leg.br/noticias/1313021-gps-escolar\n"
        "    Proposta sobre rastreamento de veículos de transporte escolar."
    )

    filtered = TelegramBot._filter_jan8_stf_sources(batch)

    assert "[1] Entenda as condenações" in filtered
    assert "portal.stf.jus.br" in filtered
    assert "Projeto define regras" not in filtered
    assert "GPS obrigatório" not in filtered
    assert filtered.count("URL:") == 1


def test_jan8_stf_filter_requires_both_event_and_legal_context():
    batch = (
        "[1] Memória dos atos de 8 de janeiro\n"
        "    URL: https://example.org/memoria\n"
        "    Reportagem histórica sobre manifestações na Praça dos Três Poderes.\n\n"
        "[2] Decisões do STF sobre direito tributário\n"
        "    URL: https://www.stf.jus.br/portal/jurisprudencia\n"
        "    Acórdãos e julgamentos sobre matéria tributária."
    )

    assert TelegramBot._filter_jan8_stf_sources(batch) == ""



def test_jan8_stf_filter_rejects_non_official_jusbrasil_analysis():
    batch = (
        "[1] Entre a Legalidade e a Contradição: STF, Bolsonaro e o 8 de Janeiro\n"
        "    URL: https://www.jusbrasil.com.br/artigos/analise-stf-8-janeiro/123\n"
        "    Artigo analisa STF, Direito Internacional, direitos humanos e eventos de 8 de janeiro."
    )

    assert TelegramBot._filter_jan8_stf_sources(batch) == ""


def test_jan8_stf_filter_rejects_official_historical_report_without_specific_decision():
    batch = (
        "[2] PDF Ministro ALEXANDRE DE MORAES - stf.jus.br\n"
        "    URL: https://www.stf.jus.br/arquivo/cms/noticiaNoticiaStf/anexo/Relatorio8dejaneiro1ano.pdf\n"
        "    Relatório histórico registra invasão dos prédios em 8 de janeiro de 2023 e depredação do patrimônio público."
    )

    assert TelegramBot._filter_jan8_stf_sources(batch) == ""


def test_jan8_stf_filter_accepts_official_specific_criminal_decision():
    batch = (
        "[1] STF publica acórdão da Ação Penal sobre atos de 8 de janeiro\n"
        "    URL: https://portal.stf.jus.br/processos/detalhe.asp?incidente=0000000\n"
        "    O Supremo Tribunal Federal publicou o acórdão do julgamento da ação penal, com condenação pelos atos antidemocráticos de 8 de janeiro."
    )

    filtered = TelegramBot._filter_jan8_stf_sources(batch)

    assert "acórdão da Ação Penal" in filtered
    assert "portal.stf.jus.br" in filtered



def test_telegram_image_generation_sends_local_png_and_records_turn():
    import base64

    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    png = b"\x89PNG\r\n\x1a\n" + b"test-image"
    def fake_agent_request(method, route, payload=None, timeout=20):
        if route == "/images/status":
            return {"available": True}
        return {
            "data_url": "data:image/png;base64," + base64.b64encode(png).decode("ascii"),
            "filename": "myra.png",
        }
    bot._agent_request = fake_agent_request

    bot._generate_image_for_chat("123", "A cinematic lighthouse")

    photo_calls = [call for call in http.calls if "/sendPhoto" in call[1]]
    assert len(photo_calls) == 1
    assert photo_calls[0][4]["photo"][1] == png
    assert photo_calls[0][4]["photo"][2] == "image/png"
    assert "image_generation" not in (bot._last_error or "")


def test_telegram_photo_sender_detects_jpeg_and_rejects_unknown_bytes():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)

    assert bot._send_photo_bytes("123", b"\xff\xd8\xffjpeg", "photo.jpg")
    photo = [call for call in http.calls if "/sendPhoto" in call[1]][0][4]["photo"]
    assert photo[2] == "image/jpeg"
    assert not bot._send_photo_bytes("123", b"not-an-image", "bad.png")



def test_telegram_image_generation_reports_local_provider_setup_when_offline():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    bot._agent_request = lambda *args, **kwargs: {
        "available": False,
        "message": "ComfyUI local esta offline.",
        "setup": "Inicie ComfyUI em 127.0.0.1:8188.",
    }

    bot._generate_image_for_chat("123", "A cinematic lighthouse")

    sent = [call for call in http.calls if "/sendMessage" in call[1]]
    assert "ComfyUI local esta offline." in sent[-1][2]["text"]
    assert "127.0.0.1:8188" in sent[-1][2]["text"]



def test_telegram_image_command_queues_background_generation(monkeypatch):
    import tasks.telegram_bot as module
    started = []

    class CapturedThread:
        def __init__(self, target, args, kwargs=None, name=None, daemon=None):
            self.target, self.args, self.name = target, args, name
        def start(self):
            started.append((self.target, self.args, self.name))

    monkeypatch.setattr(module.threading, "Thread", CapturedThread)
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    bot.handle_update(update(123, "/imagine A cinematic lighthouse"))

    assert len(started) == 1
    assert started[0][0].__name__ == "_generate_image_for_chat"
    assert started[0][1] == ("123", "A cinematic lighthouse")
    assert any("voce pode continuar conversando" in call[2]["text"] for call in http.calls if "/sendMessage" in call[1])


def test_telegram_image_status_command_reports_provider_state():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    bot._agent_request = lambda *args, **kwargs: {"available": False, "message": "ComfyUI offline.", "setup": "Start local server."}
    bot.handle_update(update(123, "/image_status"))
    sent = [call for call in http.calls if "/sendMessage" in call[1]]
    assert "ComfyUI offline." in sent[-1][2]["text"]
    assert "Start local server." in sent[-1][2]["text"]



def test_telegram_natural_language_image_request_queues_generation(monkeypatch):
    import tasks.telegram_bot as module
    started = []

    class CapturedThread:
        def __init__(self, target, args, kwargs=None, name=None, daemon=None):
            self.target, self.args = target, args
        def start(self):
            started.append((self.target, self.args))

    monkeypatch.setattr(module.threading, "Thread", CapturedThread)
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    bot._route_text_message("123", "Gere uma imagem de um farol cinematogr?fico")

    assert len(started) == 1
    assert started[0][0].__name__ == "_generate_image_for_chat"
    assert started[0][1] == ("123", "um farol cinematogr?fico")
    assert not any("11434/api/generate" in call[1] for call in http.calls)


def test_telegram_exact_user_request_with_definite_article_routes_to_image_generation(monkeypatch):
    import tasks.telegram_bot as module
    started = []

    class CapturedThread:
        def __init__(self, target, args, kwargs=None, name=None, daemon=None):
            self.target, self.args = target, args
        def start(self):
            started.append((self.target, self.args))

    monkeypatch.setattr(module.threading, "Thread", CapturedThread)
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    bot._route_text_message("123", "Gere a imagem de um gato com um Vídeo game")

    assert len(started) == 1
    assert started[0][0].__name__ == "_generate_image_for_chat"
    assert started[0][1] == ("123", "um gato com um Vídeo game")
    assert any("/sendMessage" in call[1] and "Estou gerando a imagem localmente" in call[2]["text"] for call in http.calls)


def test_telegram_image_generation_serializes_jobs_for_low_vram():
    import threading

    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    bot._image_generation_lock.acquire()
    queued = threading.Event()
    routes = []

    def fake_send_message(chat_id, message):
        if "entrou na fila" in message:
            queued.set()
        return True

    def fake_agent_request(method, route, payload=None, timeout=20):
        routes.append(route)
        return {"available": False, "message": "ComfyUI offline."}

    bot._send_message = fake_send_message
    bot._agent_request = fake_agent_request
    worker = threading.Thread(
        target=bot._generate_image_for_chat,
        args=("123", "A lighthouse"),
        daemon=True,
    )
    worker.start()

    assert queued.wait(1)
    assert routes == []
    bot._image_generation_lock.release()
    worker.join(timeout=2)

    assert not worker.is_alive()
    assert routes == ["/images/status"]
    assert not bot._image_generation_lock.locked()
