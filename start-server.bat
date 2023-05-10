@echo off
:loop
python printform-server.py
echo Restarting...
timeout /t 0 > nul
goto loop