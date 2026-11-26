@echo off
REM Rakshak demo: double-click to set up (first time only) and start the demo.
setlocal
cd /d "%~dp0"
title Rakshak demo

if exist ".venv\Scripts\python.exe" goto run

echo.
echo === First-time setup (takes 2-5 minutes, needs internet) ===
set "PY="
py -3.13 -c "import sys" >nul 2>&1 && set "PY=py -3.13" && goto found
py -3.12 -c "import sys" >nul 2>&1 && set "PY=py -3.12" && goto found
py -3.11 -c "import sys" >nul 2>&1 && set "PY=py -3.11" && goto found
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1 && set "PY=python" && goto found
echo.
echo Python 3.11 or newer was not found.
echo Install it from https://www.python.org/downloads/ (tick "Add python.exe to PATH"), then run this file again.
pause
exit /b 1

:found
echo Using %PY%
%PY% -m venv .venv
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo Setup complete.

:run
if not exist "demo\frontend\dist\index.html" (
  echo The web UI build is missing: demo\frontend\dist. Download the repo again.
  pause
  exit /b 1
)
echo.
echo === Starting Rakshak demo at http://127.0.0.1:8000 ===
echo Keep this window open during the demo. Close it to stop.
echo.
start "" cmd /c "timeout /t 5 /nobreak >nul & start http://127.0.0.1:8000"
".venv\Scripts\python.exe" -m demo.backend --port 8000
pause
exit /b 0

:fail
echo.
echo Setup failed. Check the internet connection, delete the .venv folder, and run this file again.
if exist ".venv" rmdir /s /q ".venv"
pause
exit /b 1
