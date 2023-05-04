@echo off
:loop
python printform.py
echo Restarting...
timeout /t 0 > nul
goto loop