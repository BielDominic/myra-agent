!macro NSIS_HOOK_PREUNINSTALL
  DeleteRegKey HKCU "Software\Classes\AppUserModelId\com.myra.widget"
!macroend
