@echo off
chcp 65001 >nul
:: ============================================================
::  PhotoBearRate — Iniciador único con watchdog
::  Doble clic mantiene el servidor corriendo y lo reinicia
::  si se cae. CTRL+C para detener.
:: ============================================================

cd /d "%~dp0"

cls
echo =========================================
echo   PhotoBearRate - Iniciador con watchdog
echo =========================================
echo.
echo Verificando proceso... si el servidor ya corre se reanuda el monitoreo.
echo.

:loop
powershell -NoProfile -Command "if (-not (Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*app.py*' -and $_.CommandLine -notlike '*powershell*' -and $_.CommandLine -notlike '*IniciarPhotoBearRate*' })) { Start-Process python -ArgumentList 'app.py' -WorkingDirectory '%CD%' -WindowStyle Hidden }"
timeout /t 10 /nobreak >nul
goto loop
