import subprocess
import io
import time
from flask import Blueprint, request, redirect, url_for, flash, jsonify, send_file, Response
from flask_login import login_required, current_user
from models import db, AppConfig
from datetime import datetime

admin_connect_bp = Blueprint('admin_connect', __name__, url_prefix='/admin/connect')
CF_NO_WIN = 0x08000000  # CREATE_NO_WINDOW on Windows

_STATUS_CACHE = {'ts_url': None, 'ts_running': None, 'cached_at': 0}
_STATUS_TTL = 60


def _guard():
    return not current_user.is_authenticated or not current_user.is_superuser


def _get(key, default=''):
    cfg = AppConfig.query.filter_by(key=key).first()
    return cfg.value if cfg else default


def _set(key, value):
    cfg = AppConfig.query.filter_by(key=key).first()
    if cfg:
        cfg.value = value
    else:
        db.session.add(AppConfig(key=key, value=value))
    db.session.commit()


def _is_running(pid):
    if not pid:
        return False
    try:
        r = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'],
                           capture_output=True, text=True)
        return str(pid) in r.stdout
    except Exception:
        return False


def _kill(pid):
    try:
        subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                       capture_output=True)
    except Exception:
        pass


# ── STATUS ──────────────────────────────────────────────────────────────────
@admin_connect_bp.route('/status')
@login_required
def status():
    if _guard():
        return jsonify(error='No autorizado'), 403
    now = time.time()
    if now - _STATUS_CACHE['cached_at'] > _STATUS_TTL:
        _STATUS_CACHE['ts_url'] = _get_tailscale_url()
        _STATUS_CACHE['ts_running'] = _ts_is_running()
        _STATUS_CACHE['cached_at'] = now
    return jsonify(
        ts_running=_STATUS_CACHE['ts_running'],
        ts_url=_STATUS_CACHE['ts_url'],
    )


def _get_tailscale_url():
    hostname = _get('ts_hostname') or 'photobearrate'
    # Obtener el tailnet name del hostname conocido
    try:
        r = subprocess.run(['tailscale', 'status', '--json'],
                           capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            import json
            d = json.loads(r.stdout)
            self_node = d.get('Self', {})
            dns = self_node.get('DNSName', '')
            if dns:
                return 'https://' + dns.rstrip('.')
    except Exception:
        pass
    return 'https://photobearrate.tailb81e5f.ts.net'


def _ts_is_running():
    """Verifica si tailscaled está activo y conectado."""
    try:
        r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq tailscaled.exe'],
                           capture_output=True, text=True)
        return 'tailscaled.exe' in r.stdout
    except Exception:
        return False


# ── CLOUDFLARE TUNNEL ────────────────────────────────────────────────────────
@admin_connect_bp.route('/cf/save', methods=['POST'])
@login_required
def cf_save():
    if _guard():
        return redirect(url_for('game.index'))
    _set('cf_token', request.form.get('cf_token', '').strip())
    _set('cf_port', request.form.get('cf_port', '5000').strip())
    flash('Configuración de Cloudflare guardada', 'success')
    return redirect(url_for('admin.admin') + '#tabConectividad')


@admin_connect_bp.route('/cf/start', methods=['POST'])
@login_required
def cf_start():
    if _guard():
        return redirect(url_for('game.index'))
    token = _get('cf_token')
    port = _get('cf_port', '5000')
    cmd = (['cloudflared', 'tunnel', '--token', token, 'run']
           if token else
           ['cloudflared', 'tunnel', '--url', f'http://localhost:{port}'])
    try:
        proc = subprocess.Popen(cmd, creationflags=CF_NO_WIN,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _set('cf_pid', str(proc.pid))
        flash(f'Cloudflare Tunnel iniciado (PID {proc.pid})', 'success')
    except FileNotFoundError:
        flash('cloudflared no encontrado. Instálalo primero.', 'error')
    return redirect(url_for('admin.admin') + '#tabConectividad')


@admin_connect_bp.route('/cf/stop', methods=['POST'])
@login_required
def cf_stop():
    if _guard():
        return redirect(url_for('game.index'))
    _kill(_get('cf_pid'))
    _set('cf_pid', '')
    flash('Cloudflare Tunnel detenido', 'success')
    return redirect(url_for('admin.admin') + '#tabConectividad')


# ── TAILSCALE ────────────────────────────────────────────────────────────────
@admin_connect_bp.route('/ts/save', methods=['POST'])
@login_required
def ts_save():
    if _guard():
        return redirect(url_for('game.index'))
    _set('ts_email', request.form.get('ts_email', '').strip())
    _set('ts_authkey', request.form.get('ts_authkey', '').strip())
    _set('ts_hostname', request.form.get('ts_hostname', '').strip())
    _set('ts_port', request.form.get('ts_port', '5000').strip())
    flash('Configuración de Tailscale guardada', 'success')
    return redirect(url_for('admin.admin') + '#tabConectividad')


@admin_connect_bp.route('/ts/start', methods=['POST'])
@login_required
def ts_start():
    if _guard():
        return redirect(url_for('game.index'))
    authkey = _get('ts_authkey')
    hostname = _get('ts_hostname') or 'DESKTOP-71UHCUG'
    port = _get('ts_port', '5000')
    try:
        up_args = 'up'
        if authkey:
            up_args += f' --authkey {authkey}'
        if hostname:
            up_args += f' --hostname {hostname}'
        # Tailscale corre como SYSTEM, necesita elevación
        ps_cmd = (
            f'Start-Process tailscale -ArgumentList "{up_args}" '
            f'-Verb RunAs -WindowStyle Hidden -Wait; '
            f'Start-Process tailscale -ArgumentList "funnel --bg {port}" '
            f'-Verb RunAs -WindowStyle Hidden'
        )
        proc = subprocess.Popen(
            ['powershell', '-WindowStyle', 'Hidden', '-Command', ps_cmd],
            creationflags=CF_NO_WIN,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _set('ts_pid', str(proc.pid))
        _set('ts_hostname', hostname)
        flash(f'Tailscale Funnel iniciado en puerto {port} con hostname {hostname}', 'success')
    except FileNotFoundError:
        flash('tailscale no encontrado. Instálalo primero.', 'error')
    return redirect(url_for('admin.admin') + '#tabConectividad')


@admin_connect_bp.route('/ts/cert', methods=['POST'])
@login_required
def ts_cert():
    if _guard():
        return redirect(url_for('game.index'))
    hostname = _get('ts_hostname') or 'photobearrate'
    try:
        # Usar schtasks para ejecutar como SYSTEM (tailscaled corre como SYSTEM)
        subprocess.run(
            ['schtasks', '/create', '/tn', 'TsCertProvision', '/f',
             '/tr', f'tailscale cert {hostname}.tailb81e5f.ts.net',
             '/sc', 'once', '/st', '00:00', '/ru', 'SYSTEM'],
            capture_output=True, creationflags=CF_NO_WIN)
        subprocess.run(['schtasks', '/run', '/tn', 'TsCertProvision'],
                       capture_output=True, creationflags=CF_NO_WIN)
        flash('Certificado SSL provisionado. Puede tardar unos segundos.', 'success')
    except Exception as e:
        flash(f'Error provisionando certificado: {e}', 'error')
    return redirect(url_for('admin.admin') + '#tabConectividad')


@admin_connect_bp.route('/ts/stop', methods=['POST'])
@login_required
def ts_stop():
    if _guard():
        return redirect(url_for('game.index'))
    try:
        subprocess.run(
            ['powershell', '-WindowStyle', 'Hidden', '-Command',
             'Start-Process tailscale -ArgumentList "funnel --bg off" -Verb RunAs -WindowStyle Hidden -Wait'],
            creationflags=CF_NO_WIN,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    _kill(_get('ts_pid'))
    _set('ts_pid', '')
    flash('Tailscale Funnel detenido', 'success')
    return redirect(url_for('admin.admin') + '#tabConectividad')


# ── Script de instalación automática ─────────────────────────────────────────

@admin_connect_bp.route('/setup-script')
@login_required
def setup_script():
    if _guard():
        return jsonify(error='No autorizado'), 403

    ts_authkey = _get('ts_authkey', '')
    ts_hostname = _get('ts_hostname', 'photobearrate-server')
    ts_port     = _get('ts_port', '5001')
    cf_token    = _get('cf_token', '')
    cf_port     = _get('cf_port', '5001')
    ts_email    = _get('ts_email', '')
    ts_pid_key  = _get('ts_pid', '')
    generated   = datetime.now().strftime('%Y-%m-%d %H:%M')

    cf_block = ''
    if cf_token:
        cf_block = f'''
# ══════════════════════════════════════════════
# 3. CLOUDFLARE TUNNEL
# ══════════════════════════════════════════════
Write-Host "`n[3/4] Configurando Cloudflare Tunnel..." -ForegroundColor Cyan

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {{
    Write-Host "  Descargando cloudflared..." -ForegroundColor Yellow
    $cfMsi = "$env:TEMP\\cloudflared.msi"
    Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.msi" -OutFile $cfMsi
    Start-Process msiexec.exe -ArgumentList "/i `"$cfMsi`" /quiet /norestart" -Wait
    Write-Host "  cloudflared instalado." -ForegroundColor Green
}} else {{
    Write-Host "  cloudflared ya estaba instalado." -ForegroundColor Green
}}

Write-Host "  Iniciando Cloudflare Tunnel (background)..." -ForegroundColor Yellow
Start-Process -FilePath "cloudflared" -ArgumentList "tunnel --token {cf_token} run" -WindowStyle Hidden
Write-Host "  Cloudflare Tunnel activo." -ForegroundColor Green
'''

    script = f'''# ============================================================
#  PhotoBearRate — Script de instalacion completa
#  Generado: {generated}
#  Email Tailscale: {ts_email or '(no configurado)'}
# ============================================================
#
#  INSTRUCCIONES:
#  1. Descomprime el respaldo ZIP en la carpeta destino
#  2. Ejecuta este script como Administrador
#     (clic derecho > Ejecutar con PowerShell)
#  3. Espera a que termine y luego abre la app
#
# ============================================================

$ErrorActionPreference = "Stop"

# ── Configuracion embebida ───────────────────────────────────
$APP_PORT     = "{ts_port}"
$TS_AUTHKEY   = "{ts_authkey}"
$TS_HOSTNAME  = "{ts_hostname}"
$CF_TOKEN     = "{cf_token}"
$SCRIPT_DIR   = Split-Path -Parent $MyInvocation.MyCommand.Path
# ─────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "======================================================" -ForegroundColor Magenta
Write-Host "  PhotoBearRate - Instalacion automatica" -ForegroundColor Magenta
Write-Host "======================================================" -ForegroundColor Magenta
Write-Host ""

# ══════════════════════════════════════════════
# 1. DEPENDENCIAS PYTHON
# ══════════════════════════════════════════════
Write-Host "[1/4] Instalando dependencias Python..." -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {{
    Write-Host "  ERROR: Python no encontrado." -ForegroundColor Red
    Write-Host "  Descarga Python 3.11+ desde https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "  y marca 'Add Python to PATH' al instalar." -ForegroundColor Yellow
    pause
    exit 1
}}

$reqFile = Join-Path $SCRIPT_DIR "requirements.txt"
if (Test-Path $reqFile) {{
    python -m pip install --upgrade pip --quiet
    python -m pip install -r $reqFile --quiet
    Write-Host "  Dependencias instaladas." -ForegroundColor Green
}} else {{
    Write-Host "  ADVERTENCIA: requirements.txt no encontrado en $SCRIPT_DIR" -ForegroundColor Yellow
}}

# ══════════════════════════════════════════════
# 2. TAILSCALE + FUNNEL
# ══════════════════════════════════════════════
Write-Host "`n[2/4] Configurando Tailscale Funnel..." -ForegroundColor Cyan

if (-not (Get-Command tailscale -ErrorAction SilentlyContinue)) {{
    Write-Host "  Descargando Tailscale..." -ForegroundColor Yellow
    $tsExe = "$env:TEMP\\tailscale-setup.exe"
    Invoke-WebRequest -Uri "https://pkgs.tailscale.com/stable/tailscale-setup-latest.exe" -OutFile $tsExe
    Start-Process -FilePath $tsExe -ArgumentList "/S" -Wait
    # Recargar PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    Write-Host "  Tailscale instalado." -ForegroundColor Green
}} else {{
    Write-Host "  Tailscale ya estaba instalado." -ForegroundColor Green
}}

Write-Host "  Iniciando sesion en Tailscale..." -ForegroundColor Yellow
if ($TS_AUTHKEY) {{
    tailscale up --authkey $TS_AUTHKEY --hostname $TS_HOSTNAME --accept-routes --reset 2>&1 | Out-Null
}} else {{
    Write-Host "  Sin authkey — se abrira navegador para autenticacion manual." -ForegroundColor Yellow
    tailscale up --hostname $TS_HOSTNAME --accept-routes 2>&1 | Out-Null
}}

Write-Host "  Activando Funnel en puerto $APP_PORT..." -ForegroundColor Yellow
tailscale funnel --bg $APP_PORT 2>&1 | Out-Null
Write-Host "  Tailscale Funnel activo." -ForegroundColor Green
{cf_block}
# ══════════════════════════════════════════════
# 4. TAREA PROGRAMADA (arranque automatico)
# ══════════════════════════════════════════════
Write-Host "`n[4/4] Configurando arranque automatico..." -ForegroundColor Cyan

$vbsPath = Join-Path $SCRIPT_DIR "iniciar_app.vbs"
if (Test-Path $vbsPath) {{
    $action  = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$vbsPath`""
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 0) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    Register-ScheduledTask -TaskName "PhotoBearRate" -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force | Out-Null
    Write-Host "  Tarea programada 'PhotoBearRate' creada (arranca al iniciar sesion)." -ForegroundColor Green
}} else {{
    Write-Host "  iniciar_app.vbs no encontrado — saltando tarea programada." -ForegroundColor Yellow
}}

# ══════════════════════════════════════════════
# RESUMEN
# ══════════════════════════════════════════════
Write-Host ""
Write-Host "======================================================" -ForegroundColor Green
Write-Host "  Instalacion completada" -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Green
Write-Host "  App local  : http://localhost:$APP_PORT" -ForegroundColor White
Write-Host "  Tailscale  : ejecuta 'tailscale ip' para ver la IP" -ForegroundColor White
Write-Host "  Iniciar app: doble clic en iniciar_app.vbs" -ForegroundColor White
Write-Host ""
Write-Host "Presiona cualquier tecla para cerrar..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
'''

    return Response(
        script,
        mimetype='text/plain; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename="Instalar_PhotoBearRate.ps1"'}
    )
