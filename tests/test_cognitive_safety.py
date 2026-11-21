from tasks import cognitive_core as core


def test_scheduled_context_blocks_mutating_tools(tmp_path, monkeypatch):
    monkeypatch.setenv("MYRA_COGNITIVE_DB", str(tmp_path / "safe.sqlite3"))
    called = []
    item = core.create_schedule("Read only", "Check inbox", 60)
    def executor(prompt):
        assert core.is_scheduled_execution()
        assert core.is_safe_scheduled_tool("email_read")
        assert not core.is_safe_scheduled_tool("email_send")
        called.append(prompt)
        return "checked"
    core.run_due_schedules(executor, now=item["next_run"] + 1)
    assert called == ["Check inbox"]
    assert not core.is_scheduled_execution()


def test_trace_feedback_falls_back_after_repeated_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("MYRA_COGNITIVE_DB", str(tmp_path / "learn.sqlite3"))
    for _ in range(6):
        core.record_trace("tool_call", agent="research", tool="web_search_structured", ok=False)
    route = core.route_agent("Pesquise fontes atuais sobre robótica")
    assert route["agent"] == "general"
    assert route["reason"] == "low_historical_success_fallback"
