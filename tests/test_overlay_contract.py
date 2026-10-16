# -*- coding: utf-8 -*-
"""Static contract tests for the TARS overlay (no desktop or Ollama needed)."""
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TarsOverlayContractTests(unittest.TestCase):
    def test_tauri_config_has_hidden_transparent_overlay_window(self):
        config = json.loads((ROOT / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8"))
        windows = {window["label"]: window for window in config["app"]["windows"]}
        self.assertIn("main", windows)
        self.assertIn("overlay", windows)
        overlay = windows["overlay"]
        self.assertEqual(overlay["url"], "overlay.html")
        self.assertTrue(overlay["transparent"])
        self.assertTrue(overlay["fullscreen"])
        self.assertFalse(overlay["visible"])

    def test_main_html_is_valid_entrypoint_and_keeps_tauri_logic(self):
        html = (ROOT / "src" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "src" / "tauri-widget.js").read_text(encoding="utf-8")
        self.assertTrue(html.lstrip().lower().startswith("<!doctype html>"))
        self.assertIn('src="tauri-widget.js"', html)
        self.assertIn("set_overlay_visible", script)
        self.assertIn("setWindowSize", script)

    def test_overlay_consumes_sse_and_renders_target_trajectory(self):
        html = (ROOT / "src" / "overlay.html").read_text(encoding="utf-8")
        js = (ROOT / "src" / "overlay.js").read_text(encoding="utf-8")
        css = (ROOT / "src" / "overlay.css").read_text(encoding="utf-8")
        self.assertIn('src="overlay.js"', html)
        self.assertIn('new EventSource(API + "/task_events")', js)
        self.assertIn("target_x", js)
        self.assertIn("moveCursor", js)
        self.assertIn("trail", js)
        self.assertIn("pointer-events: none", css)

    def test_native_overlay_is_click_through_and_has_visibility_command(self):
        rust = (ROOT / "src-tauri" / "src" / "lib.rs").read_text(encoding="utf-8")
        self.assertIn("set_ignore_cursor_events(true)", rust)
        self.assertIn("fn set_overlay_visible", rust)
        self.assertIn("set_overlay_visible", rust[rust.index("generate_handler!") :])

    def test_vision_tools_publish_target_before_action(self):
        agent = (ROOT / "agent.py").read_text(encoding="utf-8")
        self.assertIn("def _overlay_emit_target", agent)
        self.assertIn('"vision_click", _t_vision_click', agent)
        self.assertIn('"vision_type", _t_vision_type', agent)
        self.assertIn("time.sleep(0.22)", agent)


if __name__ == "__main__":
    unittest.main()
