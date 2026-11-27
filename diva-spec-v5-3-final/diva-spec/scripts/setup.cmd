@echo off
setlocal
cd /d "%~dp0"

echo.
echo  Diva Store Setup
echo  ================
echo.

rem WSL2 and Docker need Administrator. Re-launch this script elevated and
rem wait for it, so the SFX does not delete the temporary payload while the
rem elevated copy is still reading it.
net session >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
    echo Requesting Administrator permission...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs -Wait"
    exit /b %ERRORLEVEL%
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -PayloadDir "%~dp0."
set RC=%ERRORLEVEL%

if not "%RC%"=="0" (
    echo.
    echo Diva Store setup exited with code %RC%.
    echo Details: %TEMP%\diva-install.log
    echo.
    pause
)

exit /b %RC%
