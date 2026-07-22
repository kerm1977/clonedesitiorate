@echo off
chcp 65001 >nul
echo ========================================
echo Creando respaldo del codigo de arranque
echo ========================================
echo.

cd /d "%~dp0"

set TIMESTAMP=%date:~6,4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set BACKUP_DIR=respaldo_arranque_%TIMESTAMP%
set BACKUP_FILE=respaldo_arranque_%TIMESTAMP%.zip

echo Creando directorio de respaldo: %BACKUP_DIR%
mkdir "%BACKUP_DIR%"

echo.
echo Copiando archivos de arranque...
copy iniciar_app.vbs "%BACKUP_DIR%\" >nul
copy iniciar_watcher.vbs "%BACKUP_DIR%\" >nul
copy zombie_watcher.py "%BACKUP_DIR%\" >nul
copy instalar_acceso_directo.bat "%BACKUP_DIR%\" >nul
copy instalar_servicio.bat "%BACKUP_DIR%\" >nul
copy instalar_tarea.bat "%BACKUP_DIR%\" >nul
copy README_ZOMBIE.md "%BACKUP_DIR%\" >nul
copy config.json "%BACKUP_DIR%\" >nul

echo.
echo Creando archivo ZIP...
powershell -Command "Compress-Archive -Path '%BACKUP_DIR%\*' -DestinationPath '%BACKUP_FILE%' -Force"

echo.
echo Limpiando directorio temporal...
rmdir /s /q "%BACKUP_DIR%"

echo.
echo ========================================
echo Respaldo creado exitosamente!
echo ========================================
echo.
echo Archivo: %BACKUP_FILE%
echo.
echo Para restaurar:
echo 1. Extrae el archivo ZIP
echo 2. Copia los archivos al directorio del proyecto
echo 3. Ejecuta instalar_acceso_directo.bat para reinstalar
echo.
pause
