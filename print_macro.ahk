#Persistent ; Keeps the script running
#IfWinActive ahk_class CabinetWClass ; Only works if Windows Explorer is the active window

^!p:: ; Control + Alt + P hotkey
    Send, {Shift Down}{F10}{Shift Up} ; Simulates pressing Shift + F10 to open the context menu for the highlighted item
    Sleep, 100 ; Adds a delay to allow the context menu to appear
    Send, {Down 7}{Enter} ; Simulates pressing Down 7 times and then Enter
    Sleep, 100 ; Adds a delay to allow the print dialog to appear
    Send, {Tab 5} ; Simulates pressing Tab 5 times
return

#IfWinActive ; Ends the condition for the Windows Explorer window
