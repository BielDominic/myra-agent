import time
from tasks import cognitive_core as core


def test_route_specialists():
    assert core.classify_agent("Pesquise fontes atuais sobre robótica")["agent"] == "research"
    assert core.classify_agent("Corrija este bug Python")["agent"] == "developer"
    assert core.classify_agent("Abra o navegador e clique no botão")["agent"] == "browser"
    assert core.classify_agent("Analise esta imagem", has_image=True)["agent"] == "vision"
    assert core.classify_agent("Abra o aplicativo no meu computador")["agent"] == "computer"


def test_memory_index_and_search(tmp_path, monkeypatch):
    monkeypatch.setenv("MYRA_COGNITIVE_DB", str(tmp_path / "cognitive.sqlite3"))
    core.index_text("project", "p1", "MYRA architecture", "The MYRA project uses a local agent orchestration architecture.")
    results = core.search_memory("local agent orchestration")
    assert results and results[0]["title"] == "MYRA architecture"
    assert results[0]["retrieval"] in {"fts5", "ollama-embedding"}


def test_trace_metrics(tmp_path, monkeypatch):
    monkeypatch.setenv("MYRA_COGNITIVE_DB", str(tmp_path / "cognitive.sqlite3"))
    core.record_trace("tool_call", tool="browser_read_page", ok=True, latency_ms=120)
    core.record_trace("tool_call", tool="browser_read_page", ok=False, latency_ms=80)
    report = core.trace_summary(30)
    assert report["tool_calls"] == 2
    assert report["successful_calls"] == 1
    assert report["success_rate"] == 0.5


def test_scheduled_operatives_and_busy_deferral(tmp_path, monkeypatch):
    monkeypatch.setenv("MYRA_COGNITIVE_DB", str(tmp_path / "cognitive.sqlite3"))
    item = core.create_schedule("Check project", "Inspect project status", 60)
    called = []
    due = item["next_run"] + 1
    assert core.run_due_schedules(lambda prompt: called.append(prompt), now=due, is_busy=lambda: True) == 0
    assert called == []
    with core._db_session() as db:
        postponed = db.execute("SELECT next_run FROM schedules WHERE id=?", (item["id"],)).fetchone()[0]
    assert postponed >= due + 59
    assert core.run_due_schedules(lambda prompt: called.append(prompt) or "ok", now=postponed + 1) == 1
    assert called == ["Inspect project status"]
    assert core.list_schedules()[0]["last_status"] == "done"


def test_widget_save_does_not_collapse_settings():
    from pathlib import Path
    source = Path("src/features.js").read_text(encoding="utf-8")
    save = source.split("function saveWidgetSettings()", 1)[1].split("function applyTheme", 1)[0]
    assert "island?.classList.contains('settings')" in save
    assert "setWindowSize('idle')" not in save
