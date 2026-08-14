@echo off
:: ============================================================
::  PhotoBearRate - UNICO archivo para iniciar el sitio.
::  Doble clic aqui. No uses ningun otro .bat, .vbs o .ps1.
::
::  Que hace:
::   1. Mata cualquier proceso viejo o en conflicto (local).
::   2. Activa Tailscale Funnel si no estaba activo (remoto/global).
::   3. Deja el servidor corriendo en segundo plano, sin ventanas.
::   4. Si el servidor se cae por cualquier razon, se reinicia solo.
::   5. Si haces doble clic varias veces, no se duplica nada.
:: ============================================================
cd /d "%~dp0"
powershell -NoProfile -Command "Start-Process -FilePath 'powershell' -ArgumentList '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"%~dp0photobear_watchdog.ps1\"' -WindowStyle Hidden"
