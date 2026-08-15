import os
import io
import mimetypes
import hashlib
import random
from flask import Blueprint, render_template, send_file, abort, current_app, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, CollectionOpinion, User, Image, ImageVote, ImageDownload
from utils import log_activity

coleccion_bp = Blueprint('coleccion', __name__, url_prefix='/coleccion')


def _can_manage_opinion(op):
    return current_user.is_superuser or current_user.username in ('nita', 'lausita', 'nitalaosita') or op.username == current_user.username

COLECCION_FOLDER = r'E:\coleccion'
THUMB_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'cache', 'coleccion_thumbs')
LOW_RES_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'cache', 'coleccion_low_res')
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif'}
VIDEO_EXTS = {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.wmv', '.m4v', '.h264', '.264', '.mpeg', '.mpg', '.3gp', '.ts'}
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


def _get_image_low_path(filename, full_path):
    if not os.path.isfile(full_path):
        return None
    os.makedirs(LOW_RES_CACHE_DIR, exist_ok=True)
    h = hashlib.md5(full_path.encode('utf-8')).hexdigest() + '.webp'
    return os.path.join(LOW_RES_CACHE_DIR, h)


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

    # Agregar imágenes de la galería para que aparezcan en Colecciones
    for img in Image.query.filter_by(active=True).all():
        if not img.filepath or not os.path.isfile(img.filepath):
            continue
        ext = os.path.splitext(img.filename)[1].lower()
        if img.is_video:
            files.append({
                'name': img.filename,
                'type': 'video',
                'mime': mimetypes.guess_type(img.filepath)[0] or 'video/mp4',
                'playable': ext in BROWSER_VIDEO_EXTS,
                'from_game': True,
                'game_id': img.id,
                'is_video': True
            })
        elif ext in IMAGE_EXTS:
            files.append({
                'name': img.filename,
                'type': 'image',
                'mime': mimetypes.guess_type(img.filepath)[0] or 'application/octet-stream',
                'from_game': True,
                'game_id': img.id,
                'is_video': False
            })

    for f in files:
        if f.get('from_game'):
            f['thumb'] = url_for('game.serve_thumbnail', image_id=f['game_id'])
            f['view_url'] = url_for('game.serve_image', image_id=f['game_id'])
            f['low_url'] = url_for('game.serve_low_image', image_id=f['game_id']) if not f['is_video'] else None
            f['download_url'] = url_for('game.download_image', image_id=f['game_id'])
            f['share_url'] = url_for('game.download_image', image_id=f['game_id'], _external=True)
        else:
            full_path = os.path.join(COLECCION_FOLDER, f['name'])
            if f['type'] == 'video':
                if _get_video_thumb(f['name'], full_path):
                    f['thumb'] = url_for('coleccion.serve_thumb', filename=f['name'])
                else:
                    f['thumb'] = None
            else:
                f['thumb'] = None
            f['view_url'] = url_for('coleccion.serve_file', filename=f['name'])
            f['low_url'] = url_for('coleccion.serve_low', filename=f['name']) if f['type'] == 'image' else None
            f['download_url'] = url_for('coleccion.serve_file', filename=f['name'], download='1')
            f['share_url'] = url_for('coleccion.serve_file', filename=f['name'], download='1', _external=True)

        all_opinions = CollectionOpinion.query.filter_by(filename=f['name']).order_by(CollectionOpinion.created_at.desc()).all()
        if f.get('from_game'):
            f['opinions'] = []
        elif is_superuser:
            f['opinions'] = all_opinions
        elif is_nita:
            f['opinions'] = [op for op in all_opinions if op.username in superuser_usernames or op.username == current_user.username]
        else:
            f['opinions'] = [op for op in all_opinions if op.username == current_user.username]

    user_id = current_user.id
    is_moderator = current_user.is_superuser or current_user.username in ('nita', 'lausita', 'nitalaosita')
    for f in files:
        if f.get('from_game'):
            img = Image.query.get(f['game_id'])
        else:
            full_path = os.path.join(COLECCION_FOLDER, f['name'])
            img = Image.query.filter_by(filepath=full_path).first()
            if not img and os.path.isfile(full_path):
                img = Image(filename=f['name'], filepath=full_path, folder=COLECCION_FOLDER, active=False)
                db.session.add(img)
                db.session.commit()
        if img:
            f['image_id'] = img.id
            f['like_count'] = ImageVote.query.filter_by(image_id=img.id, vote_type='like').count()
            f['dislike_count'] = ImageVote.query.filter_by(image_id=img.id, vote_type='dislike').count()
            f['download_count'] = ImageDownload.query.filter_by(image_id=img.id).count()
            user_vote = ImageVote.query.filter_by(image_id=img.id, user_id=user_id).first()
            f['user_vote'] = user_vote.vote_type if user_vote else None
            f['view_url'] = url_for('game.serve_image', image_id=img.id) if f.get('from_game') else f['view_url']
        f['is_moderator'] = is_moderator

    filter_type = request.args.get('filter', 'all')
    if filter_type == 'images':
        files = [f for f in files if f['type'] == 'image']
    elif filter_type == 'videos':
        files = [f for f in files if f['type'] == 'video']

    page = request.args.get('page', 1, type=int)
    per_page = 15
    random.shuffle(files)
    total = len(files)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    paginated_files = files[start:start + per_page]
    has_prev = page > 1
    has_next = page < total_pages

    if request.args.get('partial') == '1':
        return render_template('partials/coleccion_grid.html', files=paginated_files,
                               page=page, total_pages=total_pages, has_prev=has_prev, has_next=has_next,
                               filter_type=filter_type, is_moderator=is_moderator)
    return render_template('coleccion.html', files=paginated_files, superuser_usernames=superuser_usernames,
                           page=page, total_pages=total_pages, has_prev=has_prev, has_next=has_next,
                           filter_type=filter_type, is_moderator=is_moderator)


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
    if _is_safe_path(COLECCION_FOLDER, full_path) and os.path.isfile(full_path):
        mtype = mimetypes.guess_type(full_path)[0] or 'application/octet-stream'
        if request.args.get('download'):
            log_activity(current_user.username, 'download', 'collection_file', filename,
                         object_url=url_for('coleccion.serve_file', filename=filename, download=1))
            img = Image.query.filter_by(filepath=full_path).first()
            if img:
                db.session.add(ImageDownload(image_id=img.id, user_id=current_user.id,
                                             username=current_user.username))
                db.session.commit()
            return send_file(full_path, mimetype=mtype, as_attachment=True, conditional=True)
        return send_file(full_path, mimetype=mtype, conditional=True)
    # Fallback a archivos de la galería
    img = Image.query.filter(Image.filename.ilike(filename)).first()
    if img and os.path.isfile(img.filepath):
        if request.args.get('download'):
            return redirect(url_for('game.download_image', image_id=img.id))
        return redirect(url_for('game.serve_image', image_id=img.id))
    abort(404)


@coleccion_bp.route('/low/<path:filename>')
@login_required
def serve_low(filename):
    full_path = os.path.join(COLECCION_FOLDER, filename)
    if not _is_safe_path(COLECCION_FOLDER, full_path) or not os.path.isfile(full_path):
        abort(404)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in IMAGE_EXTS:
        abort(404)

    cache_path = _get_image_low_path(filename, full_path)
    if os.path.exists(cache_path):
        response = send_file(cache_path, mimetype='image/webp', conditional=True)
        response.headers['Cache-Control'] = 'public, max-age=604800'
        return response

    try:
        from PIL import Image as PILImage
        pil_img = PILImage.open(full_path)
        pil_img = pil_img.convert('RGB')
        pil_img.thumbnail((1024, 1024), PILImage.LANCZOS)
        pil_img.save(cache_path, format='WEBP', quality=30, optimize=True, method=0)

        response = send_file(cache_path, mimetype='image/webp', conditional=True)
        response.headers['Cache-Control'] = 'public, max-age=604800'
        return response
    except Exception:
        return send_file(full_path, conditional=True)


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
