# MYRA automatic updates (Windows)

The Windows NSIS installer bundles the updater and a small background watcher. The installer creates a shortcut in the current user's Startup folder; no administrator-only scheduled task is required.

The watcher checks for a newer stable GitHub Release at Windows logon and every six hours. It compares semantic versions with the installed MYRA version, downloads only the matching x64 NSIS installer and SHA256SUMS.txt, verifies the installer SHA-256, and runs the installer silently only when both myra-widget.exe and the MYRA Python backend are stopped.

If MYRA or its backend is open, the update is deferred to the next check. Network failures, missing release assets, invalid version tags, and checksum mismatches fail closed; an unverified installer is never executed. Logs are written to %LOCALAPPDATA%\\MYRA\\logs\\auto-update.log.

The watcher exits when MYRA is uninstalled. The updater does not pull or overwrite a developer's Git working tree; source updates remain a separate development workflow, protecting uncommitted local changes.
