# Zombie Watcher - Reinicio Automático

## ¿Qué hace?
El Zombie Watcher monitorea la aplicación Flask y la reinicia automáticamente si:
- La app se cierra o falla
- Se pierde la conexión
- Se reinicia el equipo

## Instalación

### Opción 1: Acceso directo en Inicio (Recomendado - No requiere admin)
Ejecuta:
```batch
instalar_acceso_directo.bat
```

Esto creará un acceso directo en la carpeta de Inicio de Windows que:
- Se inicia automáticamente al iniciar sesión
- Se ejecuta en segundo plano sin ventana
- Reinicia la app Flask automáticamente

### Opción 2: Instalar como servicio de Windows (Requiere admin)
Ejecuta como administrador:
```batch
instalar_servicio.bat
```

### Opción 3: Ejecutar manualmente
Doble clic en `iniciar_watcher.vbs` para iniciar el watcher sin ventana.

## Comandos útiles

### Para acceso directo:
```batch
# Eliminar acceso directo
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\PhotoBearZombie.lnk"
```

### Para servicio (si se instaló con NSSM):
```batch
nssm start PhotoBearZombie      # Iniciar servicio
nssm stop PhotoBearZombie       # Detener servicio
nssm restart PhotoBearZombie   # Reiniciar servicio
nssm status PhotoBearZombie    # Ver estado
nssm remove PhotoBearZombie    # Eliminar servicio
```

## Logs
El watcher guarda logs en `zombie_watcher.log` con información de:
- Inicios y reinicios de la app
- Errores detectados
- Estado del proceso

## Configuración
En `zombie_watcher.py` puedes modificar:
- `CHECK_INTERVAL` = 10 (segundos entre verificaciones)
- `APP_SCRIPT` = "app.py" (script a monitorear)
- `LOG_FILE` = "zombie_watcher.log" (archivo de log)
