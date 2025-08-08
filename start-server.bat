@echo off
setlocal
echo Starting PrintForm Server with auto-restart...

set firstRun=true

:loop
echo [%date% %time%] Starting server...

REM Start the server in background
start "" /b python printform-server.py

REM Wait for the server to be ready (simple retry logic on the port)
:wait_server
timeout /t 1 > nul
powershell -command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:5000' -UseBasicParsing -TimeoutSec 1 } catch { exit 1 }"
if errorlevel 1 goto wait_server

REM Run companion programs only on first run
if "%firstRun%"=="true" (
    echo Server is up. Launching companion programs...
    start "" "C:\Program Files\Mozilla Firefox\firefox.exe" "http://127.0.0.1:5000"
    start "" "C:\Program Files\Everything\Everything.exe"
    start "" explorer "C:\Users\dvchort\Desktop\printform\static\labels\generated_labels"
    set firstRun=false
)

REM Wait until server process (python) exits
:waitloop
tasklist | findstr /i "python.exe" > nul
if %errorlevel%==0 (
    timeout /t 2 > nul
    goto waitloop
)

echo [%date% %time%] Server stopped, restarting in 2 seconds...
timeout /t 2 > nul
goto loop
