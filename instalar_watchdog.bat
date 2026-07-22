@echo off
chcp 65001 >nul
echo ========================================
echo Instalando Watchdog (Flask + Funnel)
echo ========================================
echo.

cd /d "%~dp0"

echo Eliminando tareas anteriores...
schtasks /delete /tn "PhotoBearWatchdog" /f >nul 2>&1
schtasks /delete /tn "PhotoBearZombie"   /f >nul 2>&1

echo.
echo Creando tarea al inicio del sistema (sin necesidad de login)...

schtasks /create ^
  /tn "PhotoBearWatchdog" ^
  /tr "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File \"%CD%\watchdog.ps1\"" ^
  /sc onstart ^
  /ru SYSTEM ^
  /rl HIGHEST ^
  /f

if errorlevel 1 (
    echo ERROR al crear la tarea.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Tarea instalada como servicio de sistema
echo Se iniciara automaticamente al encender el PC
echo ========================================
echo.

echo Iniciando watchdog ahora...
schtasks /run /tn "PhotoBearWatchdog"

echo.
echo Listo. Revisa watchdog.log para confirmar.
pause
