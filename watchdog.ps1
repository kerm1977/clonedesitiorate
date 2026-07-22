# watchdog.ps1 - Mantiene Flask + Tailscale Funnel corriendo siempre
# Se ejecuta como tarea programada al inicio del sistema

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$appPath   = Join-Path $scriptDir "app.py"
$logFile   = Join-Path $scriptDir "watchdog.log"
$pythonExe = "python"
$port      = 8080
$checkSec  = 15

function Write-Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line
    Write-Host $line
}

function Is-FlaskRunning {
    $procs = Get-Process python -ErrorAction SilentlyContinue
    foreach ($p in $procs) {
        try {
            $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)").CommandLine
            if ($cmd -like "*app.py*") { return $true }
        } catch {}
    }
    return $false
}

function Start-Flask {
    Write-Log "Iniciando Flask..."
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $pythonExe
    $psi.Arguments = "`"$appPath`""
    $psi.WorkingDirectory = $scriptDir
    $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $psi.CreateNoWindow = $true
    [System.Diagnostics.Process]::Start($psi) | Out-Null
    Start-Sleep -Seconds 5
    Write-Log "Flask iniciado."
}

function Is-FunnelActive {
    $out = & tailscale funnel status 2>&1
    return ($out -match "8080")
}

function Start-Funnel {
    Write-Log "Iniciando Tailscale Funnel en puerto $port..."
    & tailscale funnel reset 2>&1 | Out-Null
    Start-Sleep -Seconds 2
    & tailscale funnel $port 2>&1 | Out-Null
    Start-Sleep -Seconds 3
    if (Is-FunnelActive) {
        Write-Log "Tailscale Funnel activo."
    } else {
        Write-Log "ADVERTENCIA: Funnel puede tardar unos segundos en activarse."
    }
}

# ---- LOOP PRINCIPAL ----
Write-Log "=== Watchdog iniciado ==="

while ($true) {
    try {
        # Verificar Flask
        if (-not (Is-FlaskRunning)) {
            Write-Log "Flask caido. Reiniciando..."
            Start-Flask
        }

        # Verificar Tailscale Funnel
        if (-not (Is-FunnelActive)) {
            Write-Log "Tailscale Funnel caido. Reiniciando..."
            Start-Funnel
        }
    }
    catch {
        Write-Log "ERROR en watchdog: $_"
    }

    Start-Sleep -Seconds $checkSec
}
