@echo off
:: ============================================================
::  PhotoBearRate — Instalador de un click
::  Doble clic para instalar Python deps, Tailscale y Funnel
:: ============================================================
:: Verificar que se ejecuta como Administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando permisos de Administrador...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo ======================================================
echo   PhotoBearRate - Instalacion automatica
echo ======================================================
echo.
echo NOTA: Este .bat descarga el script de instalacion
echo personalizado con tu configuracion desde el servidor.
echo.
echo Si ya tienes el archivo Instalar_PhotoBearRate.ps1
echo en esta carpeta, ejecutalo directamente con:
echo   clic derecho -^> Ejecutar con PowerShell
echo.

:: Si existe el PS1 en la misma carpeta, ejecutarlo directamente
set PS1=%~dp0Instalar_PhotoBearRate.ps1
if exist "%PS1%" (
    echo Ejecutando script de instalacion...
    powershell -ExecutionPolicy Bypass -File "%PS1%"
    goto :end
)

echo El archivo Instalar_PhotoBearRate.ps1 no esta en esta carpeta.
echo.
echo Pasos manuales:
echo 1. Abre el Panel Admin de PhotoBearRate
echo 2. Ve al tab "Respaldo"
echo 3. Haz clic en "Descargar Script de Instalacion"
echo 4. Guarda el .ps1 en esta carpeta
echo 5. Vuelve a ejecutar este .bat
echo.
pause

:end
