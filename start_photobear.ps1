$ProjectDir = "c:\Users\MINIOS\CascadeProjects\photo-rating-game"
$PythonExe = "C:\Users\MINIOS\AppData\Local\Programs\Python\Python311\python.exe"
$LogFile = Join-Path $ProjectDir "server.log"

Set-Location $ProjectDir

# Mutex a nivel de sistema operativo: si este script (o su proceso) muere,
# Windows libera el mutex automaticamente. Garantiza una sola instancia real.
$createdNew = $false
$mutex = New-Object System.Threading.Mutex($false, "Global\PhotoBearWatchdogMutex", [ref]$createdNew)

if (-not $createdNew) {
    Add-Content -Path $LogFile -Value "[$(Get-Date)] Ya hay un watchdog de PhotoBearRate corriendo. Saliendo."
    exit
}

try {
    while ($true) {
        try {
            Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue |
                ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
        } catch {}

        Add-Content -Path $LogFile -Value "[$(Get-Date)] Iniciando PhotoBearRate..."
        & $PythonExe "app.py" *>> $LogFile

        Add-Content -Path $LogFile -Value "[$(Get-Date)] El servidor se detuvo. Reiniciando en 3 segundos..."
        Start-Sleep -Seconds 3
    }
} finally {
    $mutex.ReleaseMutex()
}
