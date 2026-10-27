@echo off
setlocal
title Stop AI Team
rem ---- Settings you may change (leave empty to use the defaults) ----
set "WSL_USER="
set "WSL_DISTRO="
rem ------------------------------------------------------------------
set "ARGS="
if defined WSL_DISTRO set "ARGS=%ARGS% -d %WSL_DISTRO%"
if defined WSL_USER set "ARGS=%ARGS% -u %WSL_USER%"
wsl %ARGS% -e bash -lc "~/.local/bin/harness stop"
echo.
echo Done. Press any key to close.
pause >nul
