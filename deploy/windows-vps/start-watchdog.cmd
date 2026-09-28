@echo off
rem Starts watchdog.ps1 hidden in the background. Put a shortcut to this file
rem in the Startup folder (Win+R, type shell:startup) so it runs at sign-in.
start "" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0watchdog.ps1"
