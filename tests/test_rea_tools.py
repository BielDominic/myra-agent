import subprocess
from pathlib import Path

from tasks import rea_tools


def test_rea_rejects_targets_outside_configured_root(tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    denied = tmp_path / "denied"
    allowed.mkdir()
    denied.mkdir()
    (allowed / "package.json").write_text('{"name":"sample"}', encoding="utf-8")
    (denied / "package.json").write_text('{"name":"other"}', encoding="utf-8")
    monkeypatch.setenv("MYRA_REA_ALLOWED_ROOTS", str(allowed))

    assert rea_tools._resolve_target(str(allowed)).is_dir()
    try:
        rea_tools._resolve_target(str(denied))
    except PermissionError as exc:
        assert "fora das raizes autorizadas" in str(exc)
    else:
        raise AssertionError("Target outside allowed root should be rejected")


def test_rea_analyzer_invokes_pinned_cli_without_shell(tmp_path, monkeypatch):
    target = tmp_path / "app"
    target.mkdir()
    (target / "package.json").write_text('{"name":"app"}', encoding="utf-8")
    monkeypatch.setenv("MYRA_REA_ALLOWED_ROOTS", str(tmp_path))
    monkeypatch.setattr(rea_tools, "_node_version", lambda: (24, 20, 0))
    monkeypatch.setattr(rea_tools, "_npx_command", lambda: ["node.exe", "npx-cli.js"])
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, stdout='{"evidence":[]}', stderr="")

    monkeypatch.setattr(rea_tools.subprocess, "run", fake_run)
    result = rea_tools.rea_analyze_javascript(str(target))

    assert result["status"] == "ok"
    assert result["rea_package"] == "rea-agents@6.5.0"
    assert captured["kwargs"]["shell"] is False
    assert captured["kwargs"]["timeout"] == 240
    assert "analyze-javascript-application" in captured["command"]
    assert "--json" in captured["command"]


def test_rea_rejects_missing_or_non_project_target(tmp_path, monkeypatch):
    monkeypatch.setenv("MYRA_REA_ALLOWED_ROOTS", str(tmp_path))
    target = tmp_path / "empty"
    target.mkdir()
    result = rea_tools.rea_analyze_javascript(str(target))
    assert result["status"] == "erro"
    assert "nao parece ser um projeto JavaScript" in result["result"]


def test_rea_status_does_not_install_anything(monkeypatch):
    monkeypatch.setattr(rea_tools.shutil, "which", lambda name: "C:/node/node.exe" if name == "node" else "C:/node/npx.cmd")
    monkeypatch.setattr(
        rea_tools.subprocess, "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, stdout="v24.20.0", stderr=""),
    )
    result = rea_tools.rea_status()
    assert result["status"] == "ok"
    assert result["node_found"] is True
    assert result["npx_found"] is True
    assert "rea_analyze_javascript" in result["note"]
