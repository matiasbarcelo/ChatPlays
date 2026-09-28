@echo off
rem Use this instead of closing Remote Desktop. It hands your session to the
rem server's own screen, so it stays unlocked and OBS keeps capturing.
rem Remote Desktop disconnects right after; reconnect any time as usual.

net session >nul 2>&1 || (
  powershell -NoProfile -Command "Start-Process -Verb RunAs -FilePath '%~f0'"
  exit /b
)

for /f "skip=1 tokens=3" %%s in ('query user %USERNAME%') do (
  %windir%\System32\tscon.exe %%s /dest:console
)
