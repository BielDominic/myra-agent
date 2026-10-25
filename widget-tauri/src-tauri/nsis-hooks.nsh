!macro NSIS_HOOK_PREUNINSTALL
  ; Remove the per-user auto-start entry so uninstalling MYRA does not leave a stale command.
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "MYRA"
  ; Remove the notification identity registered by the app at runtime.
  DeleteRegKey HKCU "Software\Classes\AppUserModelId\com.myra.widget"
!macroend
