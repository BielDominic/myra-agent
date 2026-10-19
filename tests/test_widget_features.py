# -*- coding: utf-8 -*-
"""Static contracts for the widget's local productivity features."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_running_widget_has_progress_timeline_and_pause_control():
    html = (ROOT / "src" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "src" / "main.js").read_text(encoding="utf-8")
    css = (ROOT / "src" / "style.css").read_text(encoding="utf-8")
    for element_id in ("task-objective", "task-progress-fill", "task-timeline", "btn-pause-resume"):
        assert element_id in html
    assert "function renderTaskProgress(status)" in js
    assert "function pauseResumeTask()" in js
    assert "task_pause" in js
    assert "task_resume" in js
    assert ".task-progress-fill" in css
    assert ".timeline-item" in css


def test_history_and_routines_are_local_and_have_safe_limits():
    html = (ROOT / "src" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "src" / "main.js").read_text(encoding="utf-8")
    assert "task-history" in html
    assert "btn-history-clear" in html
    assert "routine-name" in html and "routine-objective" in html
    assert "btn-gpu-monitor" in html
    assert 'MYRA_HISTORY_KEY = "myra-task-history-v1"' in js
    assert 'MYRA_ROUTINES_KEY = "myra-routines-v1"' in js
    assert "MYRA_MAX_HISTORY = 30" in js
    assert "routines.length >= 20" in js
    assert "localStorage.removeItem(MYRA_HISTORY_KEY)" in js
    features = (ROOT / "src" / "features.js").read_text(encoding="utf-8")
    assert "function applyGpuMonitor()" in features
    assert "myra-gpu-monitor" in features
    assert "if (!state.gpuMonitor) return" in features


def test_keyboard_shortcuts_include_pause_and_history():
    js = (ROOT / "src" / "main.js").read_text(encoding="utf-8")
    assert 'key === "p" ? document.getElementById("btn-pause-resume")' in js
    assert 'if (key === "h")' in js
    assert 'key === "m" ? document.getElementById("btn-compact")' in js
    assert 'key === "s" ? document.getElementById("btn-sound")' in js


def test_persisted_task_id_is_published_for_resume_route():
    source = (ROOT / "tasks" / "simple_task.py").read_text(encoding="utf-8")
    assert "_widget_notify(task_id=task_id, passo_total=max_passos" in source
