@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\container-start.ps1"
if errorlevel 1 (
    echo.
    echo Container startup failed. Check the message above and Docker Desktop.
    pause
)
endlocal
