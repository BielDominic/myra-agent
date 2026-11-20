!macro NSIS_HOOK_POSTINSTALL
  DetailPrint "Configurando o backend local da MYRA..."
  ExecWait '"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\setup_backend.ps1"' $0
  ${If} $0 != 0
    MessageBox MB_ICONEXCLAMATION|MB_OK "A interface MYRA foi instalada, mas a configuracao automatica do backend nao terminou. Consulte os logs e execute novamente o setup_backend.ps1 na pasta de instalacao da MYRA. O runtime Python e os pacotes principais estao incluidos no instalador."
  ${EndIf}

  ; Local-first default: automatic GitHub update polling is disabled.
  ; The updater scripts remain available for an explicit manual update action.
  ; If the optional local ComfyUI engine is installed, start it silently at logon.
  IfFileExists "$LOCALAPPDATA\MYRA\ComfyUI\ComfyUI\main.py" comfy_startup_create comfy_startup_done
comfy_startup_create:
  CreateShortCut "$APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\MYRA Image Engine.lnk" "$SYSDIR\WindowsPowerShell\v1.0\powershell.exe" "-NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File $\"$INSTDIR\resources\start_comfyui.ps1$\"" "" 0 SW_SHOWNORMAL
comfy_startup_done:
!macroend

!macro NSIS_HOOK_POSTUNINSTALL
  Delete "$APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\MYRA Auto Update.lnk"
  Delete "$APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\MYRA Image Engine.lnk"
!macroend
