from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app, send_file
from flask_login import login_required, current_user
from models import db, User, Image, Message, AppConfig, ImageSource, Notification, PushSubscription, Story, LoginAttempt, RateLimit, Favorite, ActivityLog, ImageComment, ImageQuestion, ImageQuestionResponse, RatingFiveFeedback, ImageVote, DeletedImage
from chat_socket import _user_sids
from datetime import datetime, timedelta
import json
import os
import io
import zipfile
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

_admin_socketio = None
_chat_socketio = None

def set_admin_socketio(sio):
    global _admin_socketio
    _admin_socketio = sio

def set_chat_socketio(sio):
    global _chat_socketio
    _chat_socketio = sio

# Import and register admin stories routes
from routes.admin_stories import register_admin_stories_routes
register_admin_stories_routes(admin_bp)

# Rate limiting configuración
ADMIN_RATE_LIMIT = 30  # peticiones por minuto
ADMIN_RATE_WINDOW = 60  # segundos


def _get_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()


def rate_limit_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = _get_ip()
        now = datetime.utcnow()
        
        # Buscar o crear registro de rate limit para esta IP
        rate_record = RateLimit.query.filter_by(ip_address=ip).first()
        
        if not rate_record:
            rate_record = RateLimit(ip_address=ip, request_count=1, window_start=now)
            db.session.add(rate_record)
            db.session.commit()
        else:
            # Si la ventana de tiempo expiró, resetear
            if rate_record.window_start < now - timedelta(seconds=ADMIN_RATE_WINDOW):
                rate_record.request_count = 1
                rate_record.window_start = now
            else:
                # Incrementar contador
                rate_record.request_count += 1
                
                # Verificar si excede el límite
                if rate_record.request_count > ADMIN_RATE_LIMIT:
                    db.session.commit()
                    return jsonify({'error': 'Demasiadas peticiones. Intenta más tarde.'}), 429
            
            db.session.commit()
        
        return f(*args, **kwargs)
    return decorated_function


def _guard():
    return not current_user.is_authenticated or not current_user.is_superuser


@admin_bp.route('')
@login_required
@rate_limit_admin
def admin():
    if _guard():
        return redirect(url_for('game.index'))
    def _cfg(k, d=''): c = AppConfig.query.filter_by(key=k).first(); return c.value if c else d
    
    # Contar videos y archivos en colección
    videos_count = sum(1 for img in Image.query.all() if img.is_video)
    coleccion_folder = r'E:\coleccion'
    coleccion_count = 0
    if os.path.isdir(coleccion_folder):
        for name in os.listdir(coleccion_folder):
            if os.path.isfile(os.path.join(coleccion_folder, name)):
                ext = os.path.splitext(name)[1].lower()
                if ext in {'.jpg','.jpeg','.png','.gif','.bmp','.webp','.heic','.heif','.mp4','.webm','.mov','.avi','.mkv'}:
                    coleccion_count += 1
    
    # Obtener log de compresión si existe
    compress_log = session.pop('compress_log', None)
    
    nita_online = 'nitalaosita' in _user_sids or 'nita' in _user_sids

    return render_template('admin.html',
        nita_online=nita_online,
        messages=Message.query.order_by(Message.created_at.desc()).all(),
        images=Image.query.order_by(Image.created_at.desc()).all(),
        images_count=Image.query.count(),
        videos_count=videos_count,
        coleccion_count=coleccion_count,
        sources=ImageSource.query.order_by(ImageSource.created_at).all(),
        upload_sources=ImageSource.query.filter_by(source_type='upload', active=True).all(),
        users=User.query.order_by(User.created_at if hasattr(User, 'created_at') else User.id).all(),
        community_title=_cfg('community_title', '¡Felicidades!'),
        community_subtitle=_cfg('community_subtitle', 'Eres parte de nuestra Comunidad.'),
        community_message=_cfg('community_message', 'PedoMoms Love'),
        blocked_ips=LoginAttempt.query.filter_by(blocked=True).order_by(LoginAttempt.last_attempt.desc()).all(),
        compress_log=compress_log)


@admin_bp.route('/favorites/stats')
@login_required
def favorites_stats():
    if _guard():
        return jsonify(error='No autorizado'), 403
    total = Favorite.query.count()
    by_session = db.session.query(
        Favorite.user_session,
        db.func.count(Favorite.id).label('cnt')
    ).group_by(Favorite.user_session).order_by(db.func.count(Favorite.id).desc()).all()
    return jsonify(total=total, by_session=[{'session': r.user_session, 'count': r.cnt} for r in by_session])


@admin_bp.route('/favorites/clear-all', methods=['POST'])
@login_required
def favorites_clear_all():
    if _guard():
        return jsonify(error='No autorizado'), 403
    Favorite.query.delete(synchronize_session=False)
    db.session.commit()
    return jsonify(success=True)


@admin_bp.route('/favorites/clear-session', methods=['POST'])
@login_required
def favorites_clear_session():
    if _guard():
        return jsonify(error='No autorizado'), 403
    uid = request.json.get('session') if request.is_json else request.form.get('session')
    if not uid:
        return jsonify(error='Sesión requerida'), 400
    Favorite.query.filter_by(user_session=uid).delete(synchronize_session=False)
    db.session.commit()
    return jsonify(success=True)


@admin_bp.route('/deleted-images/count')
@login_required
def deleted_images_count():
    if _guard():
        return jsonify(error='No autorizado'), 403
    from models import DeletedImage
    total = DeletedImage.query.count()
    # Contar imágenes eliminadas por el usuario actual
    user_deleted = DeletedImage.query.filter_by(deleted_by_user_id=current_user.id).count()
    return jsonify(total=total, user_deleted=user_deleted)


@admin_bp.route('/users/count')
def users_count():
    # Rating system removed - return 0
    return jsonify(count=0)



@admin_bp.route('/community-message', methods=['POST'])
@login_required
def update_community_message():
    if _guard():
        return redirect(url_for('game.index'))
    title = request.form.get('title', '').strip()
    subtitle = request.form.get('subtitle', '').strip()
    message = request.form.get('message', '').strip()

    for key, value in [('community_title', title), ('community_subtitle', subtitle), ('community_message', message)]:
        cfg = AppConfig.query.filter_by(key=key).first()
        if cfg:
            cfg.value = value
        else:
            db.session.add(AppConfig(key=key, value=value))

    db.session.commit()
    flash('Mensaje de comunidad actualizado', 'success')
    return redirect(url_for('admin.admin') + '#tabComunidad')


@admin_bp.route('/notifications')
@login_required
def get_notifications():
    if not (current_user.is_superuser or current_user.username in ('nita','lausita','nitalaosita')):
        return jsonify(error='No autorizado'), 403
    notifications = Notification.query.order_by(Notification.created_at.desc()).limit(10).all()
    def _cr(dt):
        return (dt - timedelta(hours=6)).strftime('%d/%m/%Y %I:%M %p') if dt else ''
    return jsonify([{
        'id': n.id,
        'message': n.message,
        'type': n.notification_type,
        'read': n.read,
        'created_at': _cr(n.created_at)
    } for n in notifications])


@admin_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    if not (current_user.is_superuser or current_user.username in ('nita','lausita','nitalaosita')):
        return jsonify(error='No autorizado'), 403
    notification = Notification.query.get_or_404(notification_id)
    notification.read = True
    db.session.commit()
    return jsonify(success=True)




# ── Bienvenida Nita ─────────────────────────────────────────────

def _cfg_get(key, default=''):
    c = AppConfig.query.filter_by(key=key).first()
    return c.value if c else default

def _cfg_set(key, value):
    c = AppConfig.query.filter_by(key=key).first()
    if c:
        c.value = value
    else:
        db.session.add(AppConfig(key=key, value=value))


@admin_bp.route('/nita-welcome')
@login_required
def nita_welcome_config():
    if _guard():
        return jsonify(error='No autorizado'), 403
    return jsonify(
        title=_cfg_get('nita_welcome_title', '¡Bienvenida! 💖'),
        emoji=_cfg_get('nita_welcome_emoji', '🌸'),
        msg=_cfg_get('nita_welcome_msg', ''),
        active=_cfg_get('nita_welcome_active', '0') == '1'
    )


@admin_bp.route('/nita-welcome/save', methods=['POST'])
@login_required
def nita_welcome_save():
    if _guard():
        return jsonify(error='No autorizado'), 403
    data = request.json or {}
    _cfg_set('nita_welcome_title', data.get('title', '¡Bienvenida! 💖').strip() or '¡Bienvenida! 💖')
    _cfg_set('nita_welcome_emoji', data.get('emoji', '🌸').strip() or '🌸')
    _cfg_set('nita_welcome_msg', data.get('msg', '').strip())
    if data.get('activate'):
        _cfg_set('nita_welcome_active', '1')
    db.session.commit()
    return jsonify(success=True)


@admin_bp.route('/nita-welcome/activate', methods=['POST'])
@login_required
def nita_welcome_activate():
    if _guard():
        return jsonify(error='No autorizado'), 403
    _cfg_set('nita_welcome_active', '1')
    db.session.commit()
    return jsonify(success=True)


@admin_bp.route('/nita-welcome/deactivate', methods=['POST'])
@login_required
def nita_welcome_deactivate():
    if _guard():
        return jsonify(error='No autorizado'), 403
    _cfg_set('nita_welcome_active', '0')
    db.session.commit()
    return jsonify(success=True)


@admin_bp.route('/nita-welcome/send-now', methods=['POST'])
@login_required
def nita_welcome_send_now():
    if _guard():
        return jsonify(error='No autorizado'), 403
    if not _chat_socketio:
        return jsonify(error='Socket no disponible'), 500
    msg = _cfg_get('nita_welcome_msg', '')
    title = _cfg_get('nita_welcome_title', '¡Bienvenida! 💖')
    emoji = _cfg_get('nita_welcome_emoji', '🌸')
    if not msg:
        return jsonify(error='Sin mensaje guardado'), 400
    
    import logging
    logging.basicConfig(filename='push_debug.log', level=logging.INFO)
    logging.info(f"[WELCOME] Enviando mensaje de bienvenida: {title}")
    
    # Emitir por socket si está online (usar socket de chat)
    _chat_socketio.emit('nita_welcome', {
        'title': title, 'emoji': emoji, 'msg': msg
    }, to='user_nitalaosita')
    
    # Enviar push si está offline
    from models import PushSubscription
    from push_helper import send_push_notification
    import json
    import os
    
    subs = PushSubscription.query.filter_by(username='nitalaosita').all()
    logging.info(f"[WELCOME] Suscripciones encontradas para nitalaosita: {len(subs)}")
    
    if subs:
        vapid_file = 'vapid_keys.json'
        if os.path.exists(vapid_file):
            with open(vapid_file, 'r') as f:
                keys = json.load(f)
            payload = json.dumps({
                'type': 'welcome',
                'title': f'{emoji} {title}',
                'body': msg[:100] + '...' if len(msg) > 100 else msg
            })
            logging.info(f"[WELCOME] Payload: {payload}")
            sent_count = 0
            for sub in subs:
                try:
                    result = send_push_notification(sub, payload, keys['private_key'])
                    if result:
                        sent_count += 1
                        logging.info(f"[WELCOME] Push enviado exitosamente")
                    else:
                        logging.info(f"[WELCOME] Push falló")
                except Exception as e:
                    logging.error(f"[WELCOME] Error enviando push: {e}")
            logging.info(f"[WELCOME] Total enviados: {sent_count}/{len(subs)}")
        else:
            logging.error(f"[WELCOME] Archivo VAPID no encontrado")
    else:
        logging.warning(f"[WELCOME] No hay suscripciones para nitalaosita")
    
    return jsonify(success=True)


# ── Botón Reportar Nita ──────────────────────────────────────────

@admin_bp.route('/nita-report')
@login_required
def nita_report_config():
    if _guard():
        return jsonify(error='No autorizado'), 403
    return jsonify(
        enabled=_cfg_get('nita_report_enabled', '0') == '1',
        title=_cfg_get('nita_report_title', '¡Gracias por reportar! 🚩'),
        emoji=_cfg_get('nita_report_emoji', '🚩'),
        msg=_cfg_get('nita_report_msg', ''),
    )


@admin_bp.route('/nita-report/save', methods=['POST'])
@login_required
def nita_report_save():
    if _guard():
        return jsonify(error='No autorizado'), 403
    data = request.json or {}
    _cfg_set('nita_report_enabled', '1' if data.get('enabled') else '0')
    _cfg_set('nita_report_title', data.get('title', '¡Gracias por reportar! 🚩').strip() or '¡Gracias por reportar! 🚩')
    _cfg_set('nita_report_emoji', data.get('emoji', '🚩').strip() or '🚩')
    _cfg_set('nita_report_msg', data.get('msg', '').strip())
    db.session.commit()
    return jsonify(success=True)


# ── Respaldo / Backup ─────────────────────────────────────────────

@admin_bp.route('/backup/download')
@login_required
def backup_download():
    if _guard():
        return jsonify(error='No autorizado'), 403

    root = current_app.root_path

    # Carpetas y archivos a incluir
    INCLUDE_DIRS = ['routes', 'templates', 'static', 'uploads', 'instance']
    INCLUDE_EXTS = {'.py', '.txt', '.json', '.md', '.vbs', '.bat', '.ps1', '.html', '.css', '.js', '.svg', '.ico', '.db'}
    EXCLUDE_DIRS = {'__pycache__', '.git', 'venv', 'env', 'nssm-2.24', 'respaldo_arranque_5', '.vscode'}
    EXCLUDE_FILES = {'cert.pem', 'key.pem', 'nssm.zip'}

    buf = io.BytesIO()
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    zip_name = f'photobearrate_backup_{ts}.zip'

    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zf:

        # Archivos en la raíz
        for fname in os.listdir(root):
            fpath = os.path.join(root, fname)
            if os.path.isfile(fpath) and fname not in EXCLUDE_FILES:
                ext = os.path.splitext(fname)[1].lower()
                if ext in INCLUDE_EXTS or fname in ('requirements.txt', 'config.json', 'vapid_keys.json'):
                    zf.write(fpath, fname)

        # Carpetas completas
        for dname in INCLUDE_DIRS:
            dpath = os.path.join(root, dname)
            if not os.path.isdir(dpath):
                continue
            for dirpath, dirnames, filenames in os.walk(dpath):
                # Excluir subdirectorios no deseados
                dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
                for fname in filenames:
                    fpath = os.path.join(dirpath, fname)
                    ext = os.path.splitext(fname)[1].lower()
                    # Incluir todos los archivos en uploads/instance (datos),
                    # y solo extensiones permitidas en el resto
                    rel = os.path.relpath(fpath, root)
                    top = rel.split(os.sep)[0]
                    if top in ('uploads', 'instance'):
                        zf.write(fpath, rel)
                    elif ext in INCLUDE_EXTS and fname not in EXCLUDE_FILES:
                        zf.write(fpath, rel)

    buf.seek(0)
    return send_file(
        buf,
        mimetype='application/zip',
        as_attachment=True,
        download_name=zip_name
    )

@admin_bp.route('/nita-activity')
@login_required
def nita_activity_history():
    if not (current_user.is_superuser or current_user.username in ('nita','lausita','nitalaosita')):
        return redirect(url_for('game.index'))
    from utils import costa_rica_str

    def _format(log):
        cr = costa_rica_str(log.created_at)
        parts = cr.split(' ')
        day = parts[0] if parts else ''
        time = parts[1] + ' ' + parts[2] if len(parts) >= 3 else cr
        image_id = None
        if log.object_type == 'image' and log.object_id:
            try:
                image_id = int(log.object_id)
            except (TypeError, ValueError):
                image_id = None
        return {
            'name': log.object_name,
            'url': log.object_url or '#',
            'username': log.username,
            'day': day,
            'time': time,
            'extra': log.extra or '',
            'image_id': image_id
        }

    likes = ActivityLog.query.filter(ActivityLog.username.in_(('nita','lausita','nitalaosita')), ActivityLog.action == 'like').order_by(ActivityLog.created_at.desc()).limit(200).all()
    dislikes = ActivityLog.query.filter(ActivityLog.username.in_(('nita','lausita','nitalaosita')), ActivityLog.action == 'dislike').order_by(ActivityLog.created_at.desc()).limit(200).all()
    downloads = ActivityLog.query.filter(ActivityLog.username.in_(('nita','lausita','nitalaosita')), ActivityLog.action == 'download').order_by(ActivityLog.created_at.desc()).limit(200).all()
    other = ActivityLog.query.filter(ActivityLog.username.in_(('nita','lausita','nitalaosita')), ~ActivityLog.action.in_(('like','dislike','download'))).order_by(ActivityLog.created_at.desc()).limit(100).all()

    return render_template('nita_activity.html',
                           likes=[_format(log) for log in likes],
                           dislikes=[_format(log) for log in dislikes],
                           downloads=[_format(log) for log in downloads],
                           other_entries=[_format(log) for log in other])


@admin_bp.route('/delete-image/<int:image_id>', methods=['POST'])
@login_required
def delete_image(image_id):
    if not (current_user.is_superuser or current_user.username in ('nita','lausita','nitalaosita')):
        return redirect(url_for('game.index'))

    img = Image.query.get(image_id)
    if not img:
        flash('Imagen no encontrada.', 'error')
        return redirect(request.referrer or url_for('admin.nita_activity_history'))

    from routes.coleccion import COLECCION_FOLDER

    def _delete_allowed(filepath):
        filepath = os.path.normpath(filepath)
        # Permitir cualquier ubicacion dentro del disco E:\
        if os.path.splitdrive(filepath)[0].upper() == 'E:':
            return True
        bases = [
            os.path.normpath(COLECCION_FOLDER),
            os.path.normpath(os.path.join(current_app.root_path, 'uploads')),
            os.path.normpath(os.path.join(current_app.root_path, 'static', 'uploads')),
        ]
        for base in bases:
            try:
                if os.path.commonpath([base, filepath]) == base:
                    return True
            except ValueError:
                continue
        return False

    target_path = img.filepath
    if not target_path or not os.path.isfile(target_path):
        # Buscar la imagen automáticamente bajo E:\ por su nombre
        if img.filename:
            for root, dirs, files in os.walk('E:\\'):
                if img.filename in files:
                    candidate = os.path.join(root, img.filename)
                    if _delete_allowed(candidate):
                        target_path = candidate
                        break

    if target_path and os.path.isfile(target_path):
        if not _delete_allowed(target_path):
            flash('La ruta del archivo no está en una carpeta permitida.', 'error')
            return redirect(request.referrer or url_for('admin.nita_activity_history'))
        try:
            os.chmod(target_path, 0o777)
            os.remove(target_path)
        except Exception as e:
            flash(f'No se pudo borrar el archivo: {e}', 'error')
            return redirect(request.referrer or url_for('admin.nita_activity_history'))

    # Borrar referencias relacionadas
    db.session.query(ImageComment).filter_by(image_id=image_id).delete(synchronize_session=False)
    questions = ImageQuestion.query.filter_by(image_id=image_id).all()
    qids = [q.id for q in questions if q.id]
    if qids:
        db.session.query(ImageQuestionResponse).filter(ImageQuestionResponse.question_id.in_(qids)).delete(synchronize_session=False)
    db.session.query(ImageQuestion).filter_by(image_id=image_id).delete(synchronize_session=False)
    db.session.query(RatingFiveFeedback).filter_by(image_id=image_id).delete(synchronize_session=False)
    db.session.query(Favorite).filter_by(image_id=image_id).delete(synchronize_session=False)
    db.session.query(ImageVote).filter_by(image_id=image_id).delete(synchronize_session=False)
    db.session.query(Message).filter_by(trigger_image_id=image_id).update({Message.trigger_image_id: None}, synchronize_session=False)

    deleted_record = DeletedImage(filename=img.filename, deleted_by_user_id=current_user.id)
    db.session.add(deleted_record)
    db.session.delete(img)
    db.session.commit()

    log_activity(current_user.username, 'delete', 'image', img.filename,
                 object_id=image_id, extra='Archivo borrado físicamente')
    flash('Imagen eliminada físicamente y referencias de la base de datos.', 'success')
    return redirect(request.referrer or url_for('admin.nita_activity_history'))
