!macro NSIS_HOOK_POSTINSTALL
  DetailPrint "Configurando o backend local da MYRA..."
  ExecWait '"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\setup_backend.ps1"' $0
  ${If} $0 != 0
    MessageBox MB_ICONEXCLAMATION|MB_OK "A interface MYRA foi instalada, mas a configuracao do backend nao terminou. Instale Python 3.14 e execute o setup_backend.ps1 na pasta de instalacao da MYRA. Consulte INSTALL_WINDOWS.md."
  ${EndIf}
!macroend
