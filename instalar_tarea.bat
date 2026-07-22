@echo off
chcp 65001 >nul
echo ========================================
echo Instalando Zombie Watcher como tarea
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] Instalando dependencia psutil...
python -m pip install psutil
if errorlevel 1 (
    echo ERROR: No se pudo instalar psutil
    pause
    exit /b 1
)
echo OK
echo.

echo [2/2] Creando tarea programada...
schtasks /delete /tn "PhotoBearZombie" /f >nul 2>&1

schtasks /create /tn "PhotoBearZombie" /tr "%CD%\iniciar_watcher.vbs" /sc onlogon /rl highest /f

if errorlevel 1 (
    echo ERROR: No se pudo crear la tarea
    pause
    exit /b 1
)

echo.
echo ========================================
echo Tarea instalada exitosamente!
echo ========================================
echo.
echo Tarea: PhotoBearZombie
echo Estado: Se iniciara automaticamente al iniciar sesion
echo.
echo Comandos utiles:
echo   schtasks /run /tn "PhotoBearZombie"    - Iniciar ahora
echo   schtasks /end /tn "PhotoBearZombie"     - Detener
echo   schtasks /delete /tn "PhotoBearZombie"  - Eliminar
echo.

echo Iniciando watcher ahora...
schtasks /run /tn "PhotoBearZombie"

echo.
echo Watcher iniciado. Verifica zombie_watcher.log para confirmar.
pause
