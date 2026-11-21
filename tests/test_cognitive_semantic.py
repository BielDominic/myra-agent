from tasks import cognitive_core as core


def test_semantic_embedding_retrieval(tmp_path, monkeypatch):
    monkeypatch.setenv("MYRA_COGNITIVE_DB", str(tmp_path / "semantic.sqlite3"))
    monkeypatch.setattr(core, "_embed", lambda text: [1.0, 0.0] if any(x in text.lower() for x in ("warehouse", "robot", "factory", "machine", "navigation")) else [0.0, 1.0])
    core.index_text("project", "robot-doc", "Robotics", "A robot navigates a warehouse using cameras and sensors.")
    result = core.search_memory("factory machine robot navigation")
    assert result
    assert result[0]["retrieval"] == "ollama-embedding"
