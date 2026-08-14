@echo off
cd /d "c:\Users\MINIOS\CascadeProjects\photo-rating-game"
set PYTHON_EXE=C:\Users\MINIOS\AppData\Local\Programs\Python\Python311\python.exe

:loop
echo [%date% %time%] Liberando puerto 8080 si esta ocupado... >> server.log
for /f "tokens=5" %%p in ('netstat -ano ^| findstr :8080 ^| findstr LISTENING') do (
    taskkill /F /PID %%p >nul 2>&1
)

echo [%date% %time%] Iniciando PhotoBearRate... >> server.log
"%PYTHON_EXE%" app.py >> server.log 2>&1

echo [%date% %time%] El servidor se detuvo. Reiniciando en 3 segundos... >> server.log
timeout /t 3 /nobreak >nul
goto loop
