# Script para mantener la aplicación Flask corriendo
# Si el proceso se cierra, se reinicia automáticamente

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$appPath = Join-Path $scriptPath "app.py"

Write-Host "=== Monitor de Aplicación Flask ===" -ForegroundColor Green
Write-Host "Directorio: $scriptPath" -ForegroundColor Yellow
Write-Host "Presiona CTRL+C para detener el monitor" -ForegroundColor Yellow
Write-Host ""

while ($true) {
    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Iniciando aplicación..." -ForegroundColor Cyan
    
    $process = Start-Process -FilePath "python" -ArgumentList $appPath -WorkingDirectory $scriptPath -PassThru -NoNewWindow
    
    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Aplicación iniciada (PID: $($process.Id))" -ForegroundColor Green
    
    # Esperar a que el proceso termine
    $process.WaitForExit()
    
    $exitCode = $process.ExitCode
    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Aplicación cerrada (Exit Code: $exitCode)" -ForegroundColor Red
    
    # Esperar 3 segundos antes de reiniciar
    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Reiniciando en 3 segundos..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
}
