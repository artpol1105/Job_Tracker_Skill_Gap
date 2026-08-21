Set WshShell = CreateObject("WScript.Shell")

WshShell.CurrentDirectory = "D:\pet_projects\Job_Tracker_Skill_Gap"

WshShell.Run "D:\pet_projects\Job_Tracker_Skill_Gap\.venv\Scripts\pythonw.exe src\bot.py", 0, False

WshShell.Run "D:\pet_projects\Job_Tracker_Skill_Gap\.venv\Scripts\pythonw.exe scheduler.py", 0, False