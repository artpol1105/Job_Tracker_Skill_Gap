Set WshShell = CreateObject("WScript.Shell")

WshShell.Run ".venv\Scripts\pythonw.exe src\bot.py", 0, False

WshShell.Run ".venv\Scripts\pythonw.exe scheduler.py", 0, False