# MYRA avatar settings

The floating widget is the only runtime surface that displays the MYRA avatar. The desktop chat has no avatar in welcome, typing, user messages, or assistant message rows. The desktop Appearance panel contains a small configuration preview only.

Both the widget Preferences panel and desktop Settings > Appearance edit the same local preference record:
- Key: myra-avatar-settings-v1
- Cross-window synchronization: storage event + BroadcastChannel myra-avatar-sync
- Avatar models: MYRA Orb, Eye MYRA, Core
- Rendering styles: animated WebGL, solid, minimal
- Color controls: body, eyes, and three animated gradient stops

The orb tracks the pointer, blinks, and the floating widget can be dragged from its non-control surface. The eyes were enlarged in the fragment shader.

Automated coverage:
- scripts/test_avatar_settings_sync.py — widget/desktop settings, cross-window propagation, and no avatar in chat messages
- scripts/test_myra_ui_smoke.py — standalone widget and task tracker
- scripts/test_myra_desktop_ui_smoke.py — desktop chat, tracker, and avatar absence
- scripts/test_live_orb_main_widget.py — main widget WebGL mount and absence of legacy mascot eyes
