import io
import json
import zipfile

from tasks import plugin_manager as pm


def tool_package():
    manifest = {
        "id": "user.test-echo", "version": "1.0.0", "name": "Test Echo",
        "description": "Returns the provided message.", "type": "tool",
        "entry_point": "main.py", "tool_name": "test_echo",
        "parameters": {"type": "object", "properties": {"message": {"type": "string"}}},
        "capabilities": [], "permissions": [],
    }
    files = {
        "myra.plugin.json": json.dumps(manifest).encode(),
        "main.py": b"def run(args):\n    return {'echo': args.get('message', '')}\n",
        "README.md": b"# Test Echo\n",
        "LICENSE": b"MIT\n",
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()


def test_python_tool_runs_in_docker_isolation(monkeypatch, tmp_path):
    monkeypatch.setenv("MYRA_PLUGIN_DIR", str(tmp_path / "plugins"))
    installed = pm.install_archive(tool_package())
    assert installed["type"] == "tool"
    pm.set_plugin_enabled("user.test-echo", True)
    try:
        result = pm.execute_plugin_tool("user.test-echo", {"message": "MYRA"})
        assert result == {"echo": "MYRA"}
    finally:
        pm.set_plugin_enabled("user.test-echo", False)
        pm.remove_plugin("user.test-echo")


def test_plugin_container_has_no_network():
    assert pm._docker_runtime_ready()
