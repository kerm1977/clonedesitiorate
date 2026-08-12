@echo off
chcp 65001 >nul
:: ============================================================
::  PhotoBearRate — Iniciador con watchdog y consola propia
::  Doble clic abre el servidor en una consola independiente.
::  Si se cierra o cae, se abre otra automaticamente.
::  CTRL+C en esta ventana lo detiene.
:: ============================================================

cd /d "%~dp0"

cls
echo =========================================
echo   PhotoBearRate - Iniciador con watchdog
echo =========================================
echo.
echo Abriendo servidor en su propia consola...
echo Cierre esta ventana solo si quiere dejar de vigilarlo.
echo.

:loop
powershell -NoProfile -Command "if (-not (Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*app.py*' -and $_.CommandLine -notlike '*powershell*' -and $_.CommandLine -notlike '*IniciarPhotoBearRate*' })) { Start-Process -FilePath cmd -ArgumentList '/k','python app.py' -WorkingDirectory '%CD%' }"
ping -n 11 127.0.0.1 >nul
goto loop
