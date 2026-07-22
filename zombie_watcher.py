import os
import sys
import time
import subprocess
import psutil
import logging
import fcntl
from datetime import datetime

# Configuración
APP_SCRIPT = "app.py"
PYTHON_EXE = sys.executable
CHECK_INTERVAL = 10  # segundos
LOG_FILE = "zombie_watcher.log"
LOCK_FILE = "zombie_watcher.lock"

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def acquire_lock():
    """Adquiere un lock para evitar múltiples instancias del watcher"""
    try:
        lock_file = open(LOCK_FILE, 'w')
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        return lock_file
    except (IOError, BlockingIOError):
        return None
    except Exception:
        # Windows no soporta fcntl, usar método alternativo
        if os.path.exists(LOCK_FILE):
            try:
                with open(LOCK_FILE, 'r') as f:
                    old_pid = int(f.read().strip())
                # Verificar si el proceso existe
                try:
                    os.kill(old_pid, 0)
                    return None  # Proceso existe, no iniciar
                except OSError:
                    pass  # Proceso no existe, continuar
            except:
                pass
        # Crear nuevo lock
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
        return open(LOCK_FILE, 'r')

def release_lock(lock_file):
    """Libera el lock"""
    try:
        if lock_file:
            lock_file.close()
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception as e:
        logger.error(f"Error liberando lock: {e}")

def is_app_running():
    """Verifica si la app Flask está corriendo"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if APP_SCRIPT in cmdline and 'zombie_watcher' not in cmdline:
                        return True, proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False, None
    except Exception as e:
        logger.error(f"Error verificando proceso: {e}")
        return False, None

def start_app():
    """Inicia la aplicación Flask"""
    try:
        logger.info("Iniciando aplicación Flask...")
        # Iniciar en segundo plano sin ventana
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        process = subprocess.Popen(
            [PYTHON_EXE, APP_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        logger.info(f"Aplicación iniciada con PID: {process.pid}")
        return process
    except Exception as e:
        logger.error(f"Error iniciando aplicación: {e}")
        return None

def kill_app(pid):
    """Mata un proceso por PID"""
    try:
        if pid:
            os.kill(pid, 9)
            logger.info(f"Proceso {pid} terminado")
    except Exception as e:
        logger.error(f"Error terminando proceso {pid}: {e}")

def main():
    lock_file = acquire_lock()
    if not lock_file:
        logger.error("Ya hay una instancia del Zombie Watcher corriendo")
        return
    
    try:
        logger.info("=== Zombie Watcher iniciado ===")
        logger.info(f"Monitoreando: {APP_SCRIPT}")
        logger.info(f"Python: {PYTHON_EXE}")
        logger.info(f"Intervalo de verificación: {CHECK_INTERVAL}s")
        
        while True:
            try:
                running, pid = is_app_running()
                
                if running:
                    logger.debug(f"App corriendo (PID: {pid})")
                else:
                    logger.warning("App NO está corriendo. Reiniciando...")
                    if pid:
                        kill_app(pid)
                    start_app()
                    logger.info("App reiniciada exitosamente")
                
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("Zombie Watcher detenido por usuario")
                break
            except Exception as e:
                logger.error(f"Error en loop principal: {e}")
                time.sleep(CHECK_INTERVAL)
    finally:
        release_lock(lock_file)

if __name__ == '__main__':
    main()
