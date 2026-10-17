"""Static contract tests for MYRA's visual overlay behavior."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_activity_border_uses_viewport_sized_overlay_layer():
    css = (ROOT / "src" / "overlay.css").read_text(encoding="utf-8")
    assert "body { position: relative; isolation: isolate; }" in css
    assert ".activity-border {" in css
    assert "position: absolute;" in css
    assert "inset: 0;" in css
    assert ".activity-border::before" in css
    assert "myra-edge-glow" in css


def test_overlay_visibility_requires_explicit_computer_activity():
    js = (ROOT / "src" / "overlay.js").read_text(encoding="utf-8")
    assert "const active = data.computer_activity === true;" in js
    assert 'state.classList.toggle("visible", active);' in js
    assert "void setOverlayVisible(false);" in js
    assert "void setOverlayVisible(true);" in js
    assert "function scheduleManualPulse" not in js
    assert "manualPulseActive" not in js
    assert "manualPulseTimer" not in js
    assert "targetDescription" not in js
    assert 'const active = next !== "idle";' in js


def test_computer_activity_is_limited_to_browser_and_desktop_tools():
    task_js = (ROOT / "tasks" / "simple_task.py").read_text(encoding="utf-8")
    backend = (ROOT / "agent.py").read_text(encoding="utf-8")
    assert "def _is_computer_activity_tool(name: str)" in task_js
    assert '("browser_", "pc_", "vision_", "computer_", "mouse_", "keyboard_", "desktop_")' in task_js
    assert 'computer_activity=_is_computer_activity_tool(ferramenta)' in task_js
    assert '"computer_activity": False' in backend
    assert 'kwargs.setdefault("computer_activity", False)' in backend