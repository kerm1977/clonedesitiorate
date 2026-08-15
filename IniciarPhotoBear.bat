@echo off
chcp 65001 >nul
:: ============================================================
::  PhotoBearRate - UNICO archivo para iniciar el sitio.
::  Doble clic aqui. No uses ningun otro .bat, .vbs o .ps1.
::
::  Que hace:
::   1. Mata cualquier proceso viejo o en conflicto (local).
::   2. Activa Tailscale Funnel si no estaba activo (remoto/global).
::   3. Deja el servidor corriendo en ESTA ventana (dejala abierta).
::   4. Si el servidor se cae por cualquier razon, se reinicia solo.
::   5. Si haces doble clic varias veces, no se duplica nada.
:: ============================================================
cd /d "%~dp0"
cls
echo =========================================
echo   PhotoBearRate
echo =========================================
echo.
echo NO CIERRES esta ventana: aqui vive el servidor.
echo Para apagar el sitio, cierra esta ventana (o CTRL+C).
echo.
echo Local:  http://127.0.0.1:8090/
echo Remoto: https://photobearrate.tailb81e5f.ts.net/ (si Tailscale Funnel esta activo)
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0photobear_watchdog.ps1"

echo.
echo El proceso del servidor termino. Presiona una tecla para cerrar.
pause >nul
