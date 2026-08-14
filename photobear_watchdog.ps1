# ============================================================
#  Motor interno de PhotoBearRate. NO EJECUTAR ESTE ARCHIVO DIRECTAMENTE.
#  Usar siempre: IniciarPhotoBear.bat (doble clic)
# ============================================================

$ProjectDir = "c:\Users\MINIOS\CascadeProjects\photo-rating-game"
$PythonExe  = "C:\Users\MINIOS\AppData\Local\Programs\Python\Python311\python.exe"
$LogFile    = Join-Path $ProjectDir "server.log"

Set-Location $ProjectDir

function Log($msg) {
    $line = "[$(Get-Date)] $msg"
    Add-Content -Path $LogFile -Value $line
    Write-Host $line
}

# --- 1) Matar cualquier proceso viejo/conflictivo (local) ---
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -and (
        $_.CommandLine -match 'app\.py' -or
        $_.CommandLine -match 'start_photobear' -or
        $_.CommandLine -match 'IniciarPhotoBearRate' -or
        $_.CommandLine -match 'photobear_watchdog'
    ) -and $_.ProcessId -ne $PID
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

Start-Sleep -Milliseconds 500

# --- 2) Asegurar Tailscale Funnel activo (remoto/global) ---
try {
    $funnelStatus = (tailscale funnel status 2>&1 | Out-String)
    if ($funnelStatus -notmatch 'Funnel on') {
        Log "Funnel no estaba activo. Activando..."
        tailscale funnel 8080 | Out-Null
    } else {
        Log "Tailscale Funnel ya estaba activo."
    }
} catch {
    Log "No se pudo verificar/activar Tailscale Funnel: $_"
}

# --- 3) Mutex de instancia unica: garantiza que nunca hayan dos watchdogs ---
$createdNew = $false
$mutex = New-Object System.Threading.Mutex($false, "Global\PhotoBearWatchdogMutex", [ref]$createdNew)

if (-not $createdNew) {
    Log "Ya hay un watchdog de PhotoBearRate corriendo. Saliendo."
    exit
}

# --- 4) Loop indestructible: si el servidor cae, se reinicia solo ---
try {
    while ($true) {
        Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue |
            ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

        Log "Iniciando PhotoBearRate..."
        $proc = Start-Process -FilePath $PythonExe -ArgumentList '"app.py"' `
            -WorkingDirectory $ProjectDir -PassThru -NoNewWindow `
            -RedirectStandardOutput (Join-Path $ProjectDir "server_stdout.log") `
            -RedirectStandardError  (Join-Path $ProjectDir "server_stderr.log")
        $proc.WaitForExit()

        Log "El servidor se detuvo. Reiniciando en 3 segundos..."
        Start-Sleep -Seconds 3
    }
} finally {
    $mutex.ReleaseMutex()
}
