@echo off
echo Starting PrintForm Server with auto-restart...

REM Open companion programs only on initial startup
echo Opening companion programs...
"C:\Program Files\Mozilla Firefox\firefox.exe" "http://127.0.0.1:5000"
"C:\Program Files\Everything\Everything.exe"
"C:\Windows\System32\explorer.exe" "C:\Users\dvchort\Desktop\printform\static\labels\generated_labels"

:loop
echo [%date% %time%] Starting server...
python printform-server.py
echo [%date% %time%] Server stopped, restarting in 2 seconds...
timeout /t 2 > nul
goto loop