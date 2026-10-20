import json
import subprocess

from tasks import remote_access


def completed(payload, returncode=0):
    return subprocess.CompletedProcess(
        ["tailscale.exe", "status", "--json"],
        returncode,
        stdout=json.dumps(payload),
        stderr="",
    )


def test_status_reports_missing_install_without_exposing_api(monkeypatch):
    monkeypatch.setattr(remote_access.shutil, "which", lambda _name: None)
    monkeypatch.setattr(remote_access.Path, "is_file", lambda _self: False)
    result = remote_access.tailscale_status()
    assert result["status"] == "not_installed"
    assert result["installed"] is False
    assert result["api_exposed"] is False


def test_status_returns_only_own_valid_tailscale_ipv4(monkeypatch):
    monkeypatch.setattr(remote_access.shutil, "which", lambda _name: "tailscale.exe")
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return completed({
            "BackendState": "Running",
            "Self": {
                "HostName": "myra-pc",
                "TailscaleIPs": ["192.168.1.50", "fd7a:115c:a1e0::1", "100.101.2.3"],
            },
            "Peer": {"peer-key": {"HostName": "other-device", "TailscaleIPs": ["100.88.0.1"]}},
        })

    monkeypatch.setattr(remote_access.subprocess, "run", fake_run)
    result = remote_access.tailscale_status()
    assert result["status"] == "connected"
    assert result["connected"] is True
    assert result["tailscale_ip"] == "100.101.2.3"
    assert result["device_name"] == "myra-pc"
    assert "Peer" not in result
    assert result["api_exposed"] is False
    assert captured["command"] == ["tailscale.exe", "status", "--json"]
    assert captured["kwargs"]["shell"] is False
    assert captured["kwargs"]["timeout"] == 8


def test_status_marks_needs_login_as_disconnected(monkeypatch):
    monkeypatch.setattr(remote_access.shutil, "which", lambda _name: "tailscale.exe")
    monkeypatch.setattr(
        remote_access.subprocess, "run",
        lambda *args, **kwargs: completed({"BackendState": "NeedsLogin", "Self": {"TailscaleIPs": []}}),
    )
    result = remote_access.tailscale_status()
    assert result["status"] == "needs_login"
    assert result["connected"] is False
    assert result["tailscale_ip"] is None


def test_status_handles_invalid_json_and_nonzero_exit(monkeypatch):
    monkeypatch.setattr(remote_access.shutil, "which", lambda _name: "tailscale.exe")
    monkeypatch.setattr(
        remote_access.subprocess, "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stdout="", stderr="error"),
    )
    result = remote_access.tailscale_status()
    assert result["status"] == "not_ready"
    assert result["api_exposed"] is False
