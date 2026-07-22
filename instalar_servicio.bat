@echo off
chcp 65001 >nul
echo ========================================
echo Instalando Zombie Watcher como servicio
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] Instalando dependencia psutil...
python -m pip install psutil
if errorlevel 1 (
    echo ERROR: No se pudo instalar psutil
    pause
    exit /b 1
)
echo OK
echo.

echo [2/3] Verificando NSSM...
where nssm >nul 2>&1
if errorlevel 1 (
    echo NSSM no encontrado. Descargando...
    powershell -Command "Invoke-WebRequest -Uri 'https://nssm.cc/release/nssm-2.24.zip' -OutFile 'nssm.zip'"
    powershell -Command "Expand-Archive -Path 'nssm.zip' -DestinationPath '.' -Force"
    set NSSM_PATH=nssm-2.24\win64\nssm.exe
) else (
    set NSSM_PATH=nssm
)
echo OK
echo.

echo [3/3] Instalando servicio...
"%NSSM_PATH%" stop PhotoBearZombie 2>nul
"%NSSM_PATH%" remove PhotoBearZombie confirm 2>nul

"%NSSM_PATH%" install PhotoBearZombie "%PYTHON_EXE%" "%CD%\zombie_watcher.py"
"%NSSM_PATH%" set PhotoBearZombie AppDirectory "%CD%"
"%NSSM_PATH%" set PhotoBearZombie DisplayName PhotoBear Zombie Watcher
"%NSSM_PATH%" set PhotoBearZombie Description Monitorea y reinicia la app Flask automaticamente
"%NSSM_PATH%" set PhotoBearZombie Start SERVICE_AUTO_START

echo.
echo ========================================
echo Servicio instalado exitosamente!
echo ========================================
echo.
echo Servicio: PhotoBearZombie
echo Estado: Se iniciara automaticamente al arrancar Windows
echo.
echo Comandos utiles:
echo   nssm start PhotoBearZombie   - Iniciar servicio
echo   nssm stop PhotoBearZombie    - Detener servicio
echo   nssm restart PhotoBearZombie - Reiniciar servicio
echo   nssm remove PhotoBearZombie  - Eliminar servicio
echo.
pause
