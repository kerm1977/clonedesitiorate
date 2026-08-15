# ============================================================
#  Motor interno de PhotoBearRate. NO EJECUTAR ESTE ARCHIVO DIRECTAMENTE.
#  Usar siempre: IniciarPhotoBear.bat (doble clic)
# ============================================================

$ProjectDir = "c:\Users\MINIOS\CascadeProjects\photo-rating-game"
$PythonExe  = "C:\Users\MINIOS\AppData\Local\Programs\Python\Python311\python.exe"
$LogFile    = Join-Path $ProjectDir "server.log"

Set-Location $ProjectDir

# Leer puerto desde config.json (default 8090 para no chocar con plantillaFlask2026)
$Port = 8090
$ConfigFile = Join-Path $ProjectDir "config.json"
if (Test-Path $ConfigFile) {
    try {
        $cfg = Get-Content $ConfigFile -Raw | ConvertFrom-Json
        if ($cfg.port) { $Port = [int]$cfg.port }
    } catch {}
}

function Log($msg) {
    $line = "[$(Get-Date)] $msg"
    Add-Content -Path $LogFile -Value $line
    Write-Host $line
}

# --- 1) Matar SOLO procesos que usen nuestro puerto (NO tocar plantillaFlask2026) ---
Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

Start-Sleep -Milliseconds 500

# --- 2) Asegurar Tailscale Funnel activo solo para nuestro puerto ---
try {
    $funnelStatus = (tailscale funnel status 2>&1 | Out-String)
    if ($funnelStatus -notmatch ":$Port") {
        Log "Activando Tailscale Funnel en puerto $Port..."
        tailscale funnel $Port | Out-Null
    } else {
        Log "Tailscale Funnel ya activo en puerto $Port."
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
        Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

        Log "Iniciando PhotoBearRate en puerto $Port..."
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
