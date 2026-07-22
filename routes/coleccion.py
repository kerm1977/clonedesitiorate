import os
import io
import mimetypes
from flask import Blueprint, render_template, send_file, abort, current_app
from flask_login import login_required

coleccion_bp = Blueprint('coleccion', __name__, url_prefix='/coleccion')

COLECCION_FOLDER = r'E:\coleccion'
THUMB_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'cache', 'coleccion_thumbs')
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
    for f in files:
        if f['type'] == 'video':
            full_path = os.path.join(COLECCION_FOLDER, f['name'])
            f['thumb'] = _get_video_thumb(f['name'], full_path)
        else:
            f['thumb'] = None
    return render_template('coleccion.html', files=files)


@coleccion_bp.route('/file/<path:filename>')
@login_required
def serve_file(filename):
    full_path = os.path.join(COLECCION_FOLDER, filename)
    if not _is_safe_path(COLECCION_FOLDER, full_path) or not os.path.isfile(full_path):
        abort(404)
    mime_type, _ = mimetypes.guess_type(full_path)
    if mime_type:
        return send_file(full_path, mimetype=mime_type)
    return send_file(full_path)


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
