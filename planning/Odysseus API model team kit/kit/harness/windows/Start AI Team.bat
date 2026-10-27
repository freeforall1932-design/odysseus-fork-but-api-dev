@echo off
setlocal
title AI Team
rem ---- Settings you may change (leave empty to use the defaults) ----
set "WSL_USER="
set "WSL_DISTRO="
rem ------------------------------------------------------------------
where wsl >nul 2>&1
if errorlevel 1 (
  echo Windows Subsystem for Linux (WSL) is not installed. See Step 1 of the guide.
  pause
  exit /b 1
)
set "ARGS="
if defined WSL_DISTRO set "ARGS=%ARGS% -d %WSL_DISTRO%"
if defined WSL_USER set "ARGS=%ARGS% -u %WSL_USER%"
echo Starting the AI team. Leave this window open while you work.
echo Closing it can stop the helpers. To start again, double-click this file again.
echo.
wsl %ARGS% -e bash -lc "~/.local/bin/harness open"
echo.
echo The AI team window ended. Press any key to close.
pause >nul
