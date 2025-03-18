@echo off
"C:\Program Files\Mozilla Firefox\firefox.exe" "http://127.0.0.1:5000"
"C:\Program Files\Everything\Everything.exe"
"C:\Windows\System32\explorer.exe" "C:\Users\dvchort\Desktop\printform\static\generated_labels"
:loop
python start-server.py
echo Restarting...
timeout /t 0 > nul
goto loop