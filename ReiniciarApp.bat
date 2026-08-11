@echo off
cd /d c:\Users\MINIOS\CascadeProjects\photo-rating-game

powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like '*app.py*'} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

timeout /t 2 /nobreak >nul

call EjecutarApp.bat
