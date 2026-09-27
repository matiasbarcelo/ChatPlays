; ChatPlays drives a virtual Xbox controller, which needs the ViGEmBus driver.
; Install it with the setup that ships inside vgamepad, unless it's already there.
!macro customInstall
  ClearErrors
  ReadRegDWORD $0 HKLM "SYSTEM\CurrentControlSet\Services\ViGEmBus" "Start"
  IfErrors 0 vigem_done
    DetailPrint "Installing the ViGEmBus virtual controller driver..."
    ExecWait '"$SYSDIR\msiexec.exe" /i "$INSTDIR\resources\backend\_internal\vgamepad\win\vigem\install\x64\ViGEmBusSetup_x64.msi" /passive /norestart' $1
    DetailPrint "ViGEmBus setup exited with code $1"
  vigem_done:
!macroend
