import io
import json
import zipfile

import pytest
from fastapi import HTTPException

from tasks import plugin_manager as pm


def make_package(plugin_id="example.safe-skill", version="1.0.0", extra=None):
    manifest = {
        "id": plugin_id,
        "version": version,
        "name": "Safe Skill",
        "description": "A declarative test skill.",
        "type": "skill",
        "entry_point": "SKILL.md",
        "capabilities": [],
        "permissions": [],
    }
    files = {
        "myra.plugin.json": json.dumps(manifest).encode(),
        "README.md": b"# Safe Skill\n",
        "LICENSE": b"MIT",
        "SKILL.md": b"# Instructions\nOnly declarative text.\n",
    }
    files.update(extra or {})
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()


def test_validate_declarative_plugin_and_sha256():
    import hashlib

    payload = make_package()
    manifest, members, digest = pm.validate_archive(payload)
    assert manifest["id"] == "example.safe-skill"
    assert len(members) == 4
    assert digest == hashlib.sha256(payload).hexdigest()


@pytest.mark.parametrize("bad_name", [
    "../outside.txt",
    "folder/../../outside.md",
    "C:/Windows/system.ini",
    "/absolute.md",
    "folder\\escape.md",
])
def test_rejects_zip_path_traversal(bad_name):
    with pytest.raises(ValueError):
        pm._safe_member_name(bad_name)


def test_rejects_executable_plugins():
    payload = make_package(extra={"run.py": b"print('unsafe')"})
    with pytest.raises(ValueError, match="apenas arquivos Markdown"):
        pm.validate_archive(payload)


def test_rejects_tool_type_and_requested_permissions():
    payload = make_package()
    with zipfile.ZipFile(io.BytesIO(payload), "r") as source:
        files = {name: source.read(name) for name in source.namelist()}
    manifest = json.loads(files["myra.plugin.json"])
    manifest["type"] = "tool"
    files["myra.plugin.json"] = json.dumps(manifest).encode()
    rebuilt = io.BytesIO()
    with zipfile.ZipFile(rebuilt, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    with pytest.raises(ValueError, match="apenas plugins declarativos"):
        pm.validate_archive(rebuilt.getvalue())


def test_rejects_permissions_on_declarative_skill():
    payload = make_package()
    with zipfile.ZipFile(io.BytesIO(payload), "r") as source:
        files = {name: source.read(name) for name in source.namelist()}
    manifest = json.loads(files["myra.plugin.json"])
    manifest["permissions"] = ["network"]
    files["myra.plugin.json"] = json.dumps(manifest).encode()
    rebuilt = io.BytesIO()
    with zipfile.ZipFile(rebuilt, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    with pytest.raises(ValueError, match="não podem solicitar"):
        pm.validate_archive(rebuilt.getvalue())


def test_install_is_disabled_by_default_and_removable(monkeypatch, tmp_path):
    monkeypatch.setenv("MYRA_PLUGIN_DIR", str(tmp_path / "plugins"))
    result = pm.install_archive(make_package())
    assert result["installed"] is True
    assert result["enabled"] is False
    assert result["permissions"] == []
    assert (tmp_path / "plugins" / "example.safe-skill" / "1.0.0" / "SKILL.md").exists()
    assert pm.list_plugins()["plugins"][0]["enabled"] is False
    removed = pm.remove_plugin("example.safe-skill")
    assert removed["removed"] is True
    assert pm.list_plugins()["plugins"] == []


def test_duplicate_version_is_rejected_without_overwrite(monkeypatch, tmp_path):
    monkeypatch.setenv("MYRA_PLUGIN_DIR", str(tmp_path / "plugins"))
    pm.install_archive(make_package())
    with pytest.raises(HTTPException) as error:
        pm.install_archive(make_package())
    assert error.value.status_code == 409
    assert (tmp_path / "plugins" / "example.safe-skill" / "1.0.0" / "SKILL.md").exists()


def test_archive_size_limit(monkeypatch):
    monkeypatch.setattr(pm, "MAX_ARCHIVE_BYTES", 8)
    with pytest.raises(ValueError, match="20 MB"):
        pm.validate_archive(make_package())
def test_plugin_http_api_validate_install_list_and_remove(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    import agent

    monkeypatch.setenv("MYRA_PLUGIN_DIR", str(tmp_path / "api-plugins"))
    monkeypatch.setattr(agent, "_telegram_startup", lambda: None)
    monkeypatch.setattr(agent, "_telegram_shutdown", lambda: None)

    payload = make_package(plugin_id="api.safe-skill")
    with TestClient(agent.app) as client:
        validated = client.post(
            "/plugins/validate",
            content=payload,
            headers={"content-type": "application/zip"},
        )
        assert validated.status_code == 200
        assert validated.json()["valid"] is True
        assert validated.json()["executable_code"] is False

        installed = client.post(
            "/plugins/install",
            content=payload,
            headers={"content-type": "application/zip"},
        )
        assert installed.status_code == 200
        assert installed.json()["enabled"] is False

        listed = client.get("/plugins")
        assert listed.status_code == 200
        assert listed.json()["plugins"][0]["id"] == "api.safe-skill"

        removed = client.delete("/plugins/api.safe-skill")
        assert removed.status_code == 200
        assert removed.json()["removed"] is True

        unsupported = client.post(
            "/plugins/install",
            content=payload,
            headers={"content-type": "text/plain"},
        )
        assert unsupported.status_code == 415
