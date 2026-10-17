from pathlib import Path

from tasks.telegram_bot import TelegramBot


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
        if "/sendPhoto" in url:
            return FakeResponse({"ok": True, "result": {"message_id": 2}})
        return FakeResponse({"ok": True, "result": {"message_id": 1}})

    def get(self, url, params=None, timeout=None):
        self.calls.append(("GET", url, params, None, None))
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


def test_see_command_returns_visual_summary():
    http = FakeHTTP()
    bot = TelegramBot(token="test-token", allowed_chat_ids={"123"}, http=http)
    bot.handle_update(update(123, "/see o que aparece?"))
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
