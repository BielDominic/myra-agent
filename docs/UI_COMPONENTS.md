# MYRA UI components

## LiveOrb (WebGL)

The old CSS-drawn mascot has been removed from the active MYRA desktop and widget shells. The replacement is a native custom element backed by the LiveOrb shader engine supplied for this project.

- Source: src/components/ui/myra-ui.js
- Styles: src/components/ui/myra-ui.css
- Widget mirror: widget/myra-ui.js and widget/myra-ui.css
- Mount point: <myra-orb data-variant="webgl" data-state="idle"></myra-orb>

The WebGL renderer uses the supplied vertex/fragment shader model, the violet/foam/dust-rose palette, pointer gaze, autonomous glances, blink animation, resize handling, visibility/reduced-motion awareness, and WebGL context-loss recovery. State values idle, working, listening, success, and error are reflected through data-state.

The React hook wrapper from the supplied TSX source is not used directly because the existing Tauri UI is static HTML/CSS/JavaScript and the app's primary desktop window is not a React application. The shader engine is mounted through a custom element so the existing chat, settings, task controls, and Tauri IPC remain intact. No second frontend runtime is loaded.

## Shining status text

The existing myra-shining-text CSS class remains in use for animated status labels. The supplied LiveOrb paste contains the LiveOrb component and demo; it does not contain a separate ShiningText source file.

## Task step tracker

window.MyraUI.renderStepTracker(host, status, options) renders the task progress card using the existing /task_status payload. The floating widget owns the visible task-step tracker; desktop chat intentionally does not duplicate it.

## Verification

Run:
- python scripts/test_live_orb_webgl.py
- python scripts/test_live_orb_main_widget.py
- python scripts/test_myra_ui_smoke.py
- python scripts/test_myra_desktop_ui_smoke.py

The WebGL tests should be run with a browser that supports WebGL (the automated Chromium test uses SwiftShader).


## Widget global cursor and desktop visibility

The Tauri widget now polls the native Windows cursor position through 'get_cursor_relative_to_window' and forwards the relative point to the active WebGL orb. This keeps the eyes tracking while the pointer is outside the compact pill/WebView. The desktop workspace exposes a top-bar eye-icon control beside the model selector that calls 'set_widget_visible' to hide/show the floating 'main' window without closing the workspace. Task-step rendering belongs to the floating widget; the desktop chat does not render a duplicate tracker. Actual save/apply/setup/model-change operations use a centered glassmorphism overlay with responsive animated bars; the loader is not shown for widget idle state or chat thinking.


## Widget appearance settings and capability reporting

There is no separate Widget Studio page. The real widget's accent palette, opacity, expanded width and expanded height are edited under Settings > Appearance and synchronized through the existing myra-widget-sync BroadcastChannel. These controls write the same myra-widget-config-v1 configuration consumed by the widget.

Capability questions are answered by a deterministic runtime inventory in agent.py. It probes local runtime, voice, model, setup, task, plugin, API-integration and ComfyUI status before listing available, configuration-dependent and unavailable features. This avoids claiming that a disabled Telegram channel, an empty plugin registry or an inactive remote API is operational.
