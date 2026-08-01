import os
import io
import mimetypes
from flask import Blueprint, render_template, send_file, abort, current_app, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, CollectionOpinion, User

coleccion_bp = Blueprint('coleccion', __name__, url_prefix='/coleccion')


def _can_manage_opinion(op):
    return current_user.is_superuser or current_user.username in ('nita', 'lausita', 'nitalaosita') or op.username == current_user.username

COLECCION_FOLDER = r'E:\coleccion'
THUMB_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'cache', 'coleccion_thumbs')
LOW_RES_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'cache', 'coleccion_low_res')
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif'}
VIDEO_EXTS = {'.mp4', '.webm', '.mov', '.avi', '.mkv'}
BROWSER_VIDEO_EXTS = {'.mp4', '.webm', '.mov'}


def _is_safe_path(base, requested):
    base = os.path.abspath(base)
    requested = os.path.abspath(requested)
    return requested.startswith(base)


def _generate_video_thumbnail(video_path, thumb_path):
    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return False
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, total // 4))
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            return False
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        from PIL import Image as PILImage
        pil_img = PILImage.fromarray(frame)
        pil_img.thumbnail((320, 320), PILImage.LANCZOS)
        pil_img.save(thumb_path, format='WEBP', quality=50)
        return True
    except Exception:
        return False


def _get_video_thumb(filename, full_path):
    os.makedirs(THUMB_CACHE_DIR, exist_ok=True)
    safe_name = filename.replace('/', '_').replace('\\', '_')
    thumb_path = os.path.join(THUMB_CACHE_DIR, safe_name + '.webp')
    if os.path.exists(thumb_path):
        return thumb_path
    if _generate_video_thumbnail(full_path, thumb_path):
        return thumb_path
    return None


def _get_low_res_path(filename, full_path):
    if not os.path.isfile(full_path):
        return None
    os.makedirs(LOW_RES_CACHE_DIR, exist_ok=True)
    base = os.path.splitext(filename)[0]
    low_path = os.path.join(LOW_RES_CACHE_DIR, base + '_low.mp4')
    return low_path if os.path.exists(low_path) else None


def _list_files():
    if not os.path.isdir(COLECCION_FOLDER):
        return []
    files = []
    for name in sorted(os.listdir(COLECCION_FOLDER)):
        full_path = os.path.join(COLECCION_FOLDER, name)
        if not os.path.isfile(full_path):
            continue
        ext = os.path.splitext(name)[1].lower()
        mime_type, _ = mimetypes.guess_type(full_path)
        if ext in IMAGE_EXTS:
            files.append({'name': name, 'type': 'image', 'mime': mime_type or 'application/octet-stream'})
        elif ext in BROWSER_VIDEO_EXTS:
            files.append({'name': name, 'type': 'video', 'mime': mime_type or 'video/mp4', 'playable': True})
        elif ext in VIDEO_EXTS:
            files.append({'name': name, 'type': 'video', 'mime': mime_type or 'application/octet-stream', 'playable': False})
    return files


@coleccion_bp.route('/')
@login_required
def index():
    files = _list_files()
    superuser_usernames = {u.username for u in User.query.filter_by(is_superuser=True).all() if u.username}
    is_superuser = current_user.is_superuser
    is_nita = current_user.username == 'nitalaosita'
    for f in files:
        if f['type'] == 'video':
            full_path = os.path.join(COLECCION_FOLDER, f['name'])
            f['thumb'] = _get_video_thumb(f['name'], full_path)
        else:
            f['thumb'] = None
        all_opinions = CollectionOpinion.query.filter_by(filename=f['name']).order_by(CollectionOpinion.created_at.desc()).all()
        if is_superuser:
            f['opinions'] = all_opinions
        elif is_nita:
            f['opinions'] = [op for op in all_opinions if op.username in superuser_usernames or op.username == current_user.username]
        else:
            f['opinions'] = [op for op in all_opinions if op.username == current_user.username]
    return render_template('coleccion.html', files=files, superuser_usernames=superuser_usernames)


@coleccion_bp.route('/opinion', methods=['POST'])
@login_required
def save_opinion():
    filename = request.form.get('filename', '').strip()
    opinion = request.form.get('opinion', '').strip()
    if not filename or not opinion:
        flash('Faltan datos para la opinión', 'warning')
        return redirect(url_for('coleccion.index'))
    full_path = os.path.join(COLECCION_FOLDER, filename)
    if not _is_safe_path(COLECCION_FOLDER, full_path) or not os.path.isfile(full_path):
        abort(404)
    db.session.add(CollectionOpinion(filename=filename, username=current_user.username, opinion=opinion))
    db.session.commit()
    flash('Opinión guardada', 'success')
    return redirect(url_for('coleccion.index'))


@coleccion_bp.route('/opinion/<int:opinion_id>/edit', methods=['POST'])
@login_required
def edit_opinion(opinion_id):
    op = CollectionOpinion.query.get_or_404(opinion_id)
    if not _can_manage_opinion(op):
        abort(403)
    new_text = request.form.get('opinion', '').strip()
    if not new_text:
        flash('La opinión no puede estar vacía', 'warning')
        return redirect(url_for('coleccion.index'))
    op.opinion = new_text
    db.session.commit()
    flash('Opinión actualizada', 'success')
    return redirect(url_for('coleccion.index'))


@coleccion_bp.route('/opinion/<int:opinion_id>/delete', methods=['POST'])
@login_required
def delete_opinion(opinion_id):
    op = CollectionOpinion.query.get_or_404(opinion_id)
    if not _can_manage_opinion(op):
        abort(403)
    db.session.delete(op)
    db.session.commit()
    flash('Opinión eliminada', 'success')
    return redirect(url_for('coleccion.index'))


@coleccion_bp.route('/file/<path:filename>')
@login_required
def serve_file(filename):
    full_path = os.path.join(COLECCION_FOLDER, filename)
    if not _is_safe_path(COLECCION_FOLDER, full_path) or not os.path.isfile(full_path):
        abort(404)
    mtype = mimetypes.guess_type(full_path)[0] or 'application/octet-stream'
    if request.args.get('download'):
        return send_file(full_path, mimetype=mtype, as_attachment=True, conditional=True)
    return send_file(full_path, mimetype=mtype, conditional=True)


@coleccion_bp.route('/low/<path:filename>')
@login_required
def serve_low(filename):
    full_path = os.path.join(COLECCION_FOLDER, filename)
    if not _is_safe_path(COLECCION_FOLDER, full_path) or not os.path.isfile(full_path):
        abort(404)
    low_path = _get_low_res_path(filename, full_path)
    if low_path and os.path.exists(low_path):
        return send_file(low_path, mimetype='video/mp4')
    abort(404)


@coleccion_bp.route('/thumb/<path:filename>')
@login_required
def serve_thumb(filename):
    full_path = os.path.join(COLECCION_FOLDER, filename)
    if not _is_safe_path(COLECCION_FOLDER, full_path) or not os.path.isfile(full_path):
        abort(404)
    thumb_path = _get_video_thumb(filename, full_path)
    if thumb_path and os.path.exists(thumb_path):
        return send_file(thumb_path, mimetype='image/webp')
    abort(404)
