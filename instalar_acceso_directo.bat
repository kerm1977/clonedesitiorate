@echo off
chcp 65001 >nul
echo ========================================
echo Instalando Zombie Watcher (Inicio automatico)
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

echo [2/2] Creando acceso directo en Inicio...
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%STARTUP%\PhotoBearZombie.lnk'); $Shortcut.TargetPath = '%CD%\iniciar_watcher.vbs'; $Shortcut.WorkingDirectory = '%CD%'; $Shortcut.Save()"

if errorlevel 1 (
    echo ERROR: No se pudo crear el acceso directo
    pause
    exit /b 1
)

echo.
echo ========================================
echo Instalacion completada!
echo ========================================
echo.
echo Acceso directo creado en: %STARTUP%\PhotoBearZombie.lnk
echo El watcher se iniciara automaticamente al iniciar sesion.
echo.

echo Iniciando watcher ahora...
start "" iniciar_watcher.vbs

echo.
echo Watcher iniciado. Verifica zombie_watcher.log para confirmar.
echo Presiona Ctrl+C para detener este script.
timeout /t 5
