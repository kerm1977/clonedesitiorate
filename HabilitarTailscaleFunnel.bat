@echo off
chcp 65001 >nul
:: ============================================================
::  Habilitar Tailscale Funnel (requiere ejecutar como admin)
::  Debe usarse UNA VEZ para darle permisos al usuario actual
::  sobre el demonio de Tailscale que corre como sistema.
:: ============================================================

cd /d "%~dp0"

cls
echo =========================================
echo   Habilitar Tailscale Funnel
echo =========================================
echo.
echo Tailscale esta corriendo como sistema (NT AUTHORITY\\SYSTEM).
echo Para que el usuario actual pueda controlarlo hay que darle permisos
echo de operador y luego iniciar el funnel al puerto 8080.
echo.
echo Se abrira una consola como administrador.
echo Acepte el mensaje UAC y espere a que termine.
echo.

powershell -NoProfile -Command "Start-Process -FilePath cmd -ArgumentList '/k cd /d %CD% && echo [1/2] Configurando operador... && tailscale up --operator=%USERNAME% && echo [2/2] Iniciando funnel en puerto 8080... && tailscale funnel 8080' -Verb RunAs"
