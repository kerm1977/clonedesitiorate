from flask import render_template, send_file, redirect, url_for, jsonify, request
from flask_login import login_required, current_user
from models import db, Image, ImageDownload
from utils import log_activity
import os
import io
import mimetypes
import hashlib
from PIL import Image as PILImage

DISK_SEARCH_FOLDER = r'D:\Nueva carpeta'
THUMB_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'cache', 'game_thumbs')
LOW_RES_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'cache', 'game_low')


def _get_game_thumb_path(filepath):
    os.makedirs(THUMB_CACHE_DIR, exist_ok=True)
    h = hashlib.md5(filepath.encode('utf-8')).hexdigest() + '.webp'
    return os.path.join(THUMB_CACHE_DIR, h)


def _get_game_low_path(filepath):
    os.makedirs(LOW_RES_CACHE_DIR, exist_ok=True)
    h = hashlib.md5(filepath.encode('utf-8')).hexdigest() + '.webp'
    return os.path.join(LOW_RES_CACHE_DIR, h)
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif'}
VIDEO_EXTS = {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.wmv', '.m4v', '.h264', '.264', '.mpeg', '.mpg', '.3gp', '.ts'}


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


def _serve_game_video_thumb(filepath):
    cache_path = _get_game_thumb_path(filepath)
    if os.path.exists(cache_path):
        return send_file(cache_path, mimetype='image/webp', conditional=True)
    if _generate_video_thumbnail(filepath, cache_path):
        return send_file(cache_path, mimetype='image/webp', conditional=True)
    return 'No disponible', 404


def register_game_images_routes(bp):
    
    @bp.route('/image/<int:image_id>')
    def view_image(image_id):
        if not current_user.is_authenticated or not current_user.is_superuser:
            return redirect(url_for('auth.login'))
        img = Image.query.get_or_404(image_id)
        log_activity(current_user.username, 'view', 'image', img.filename,
                     object_url=url_for('game.view_image', image_id=img.id),
                     object_id=img.id)
        from models import ImageVote
        like_count = ImageVote.query.filter_by(image_id=img.id, vote_type='like').count()
        dislike_count = ImageVote.query.filter_by(image_id=img.id, vote_type='dislike').count()
        download_count = ImageDownload.query.filter_by(image_id=img.id).count()
        user_vote = ImageVote.query.filter_by(image_id=img.id, user_id=current_user.id).first()
        is_moderator = current_user.is_superuser or current_user.username in ('nita', 'lausita', 'nitalaosita')
        return render_template('view_image.html', image=img, like_count=like_count,
                               dislike_count=dislike_count, download_count=download_count,
                               user_vote=user_vote.vote_type if user_vote else None,
                               is_moderator=is_moderator)

    @bp.route('/img/<int:image_id>')
    def serve_image(image_id):
        img = Image.query.get_or_404(image_id)
        if not os.path.exists(img.filepath):
            return "Imagen no encontrada", 404
        
        if current_user.is_authenticated and current_user.username in ('nitalaosita','nita','lausita'):
            log_activity(current_user.username, 'view', 'image', img.filename,
                         object_url=url_for('game.serve_image', image_id=img.id),
                         object_id=img.id)
        
        # Detectar MIME type correcto para videos
        mime_type, _ = mimetypes.guess_type(img.filepath)
        response = send_file(img.filepath, mimetype=mime_type, conditional=True) if mime_type else send_file(img.filepath, conditional=True)
        response.headers['Cache-Control'] = 'public, max-age=604800'
        return response

    @bp.route('/img/<int:image_id>/thumb')
    def serve_thumbnail(image_id):
        img = Image.query.get_or_404(image_id)
        if not os.path.exists(img.filepath):
            return "No disponible", 404

        if img.is_video:
            return _serve_game_video_thumb(img.filepath)

        cache_path = _get_game_thumb_path(img.filepath)
        if os.path.exists(cache_path):
            response = send_file(cache_path, mimetype='image/webp', conditional=True)
            response.headers['Cache-Control'] = 'public, max-age=604800'
            return response

        try:
            thumb_size = (240, 240)
            pil_img = PILImage.open(img.filepath)
            pil_img = pil_img.convert('RGB')
            pil_img.thumbnail(thumb_size, PILImage.LANCZOS)
            pil_img.save(cache_path, format='WEBP', quality=35, optimize=True, method=0)

            response = send_file(cache_path, mimetype='image/webp', conditional=True)
            response.headers['Cache-Control'] = 'public, max-age=604800'
            return response
        except Exception:
            return send_file(img.filepath, conditional=True)

    @bp.route('/img/<int:image_id>/low')
    def serve_low_image(image_id):
        img = Image.query.get_or_404(image_id)
        if img.is_video or not os.path.exists(img.filepath):
            return "No disponible", 404

        ext = os.path.splitext(img.filepath)[1].lower()
        if ext not in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}:
            return send_file(img.filepath, conditional=True)

        # Servir GIF/WEBP originales (pueden ser animados; no reconvertir)
        if ext in {'.gif', '.webp'}:
            mime_type, _ = mimetypes.guess_type(img.filepath)
            response = send_file(img.filepath, mimetype=mime_type, conditional=True) if mime_type else send_file(img.filepath, conditional=True)
            response.headers['Cache-Control'] = 'public, max-age=604800'
            return response

        cache_path = _get_game_low_path(img.filepath)
        if os.path.exists(cache_path):
            response = send_file(cache_path, mimetype='image/webp', conditional=True)
            response.headers['Cache-Control'] = 'public, max-age=604800'
            return response

        try:
            pil_img = PILImage.open(img.filepath)
            pil_img = pil_img.convert('RGB')
            pil_img.thumbnail((1024, 1024), PILImage.LANCZOS)
            pil_img.save(cache_path, format='WEBP', quality=30, optimize=True, method=0)

            response = send_file(cache_path, mimetype='image/webp', conditional=True)
            response.headers['Cache-Control'] = 'public, max-age=604800'
            return response
        except Exception:
            return send_file(img.filepath, conditional=True)

    @bp.route('/img/<int:image_id>/download')
    @login_required
    def download_image(image_id):
        img = Image.query.get_or_404(image_id)
        if not os.path.exists(img.filepath):
            return "Imagen no encontrada", 404
        log_activity(current_user.username, 'download', 'image', img.filename,
                     object_url=url_for('game.serve_image', image_id=img.id),
                     object_id=img.id)
        db.session.add(ImageDownload(image_id=img.id, user_id=current_user.id,
                                     username=current_user.username))
        db.session.commit()
        return send_file(img.filepath, as_attachment=True, download_name=img.filename, conditional=True)

    @bp.route('/search-folder')
    @login_required
    def search_folder():
        query = request.args.get('q', '').strip().lower()
        ftype = request.args.get('type', 'all')
        if not query or not os.path.isdir(DISK_SEARCH_FOLDER):
            return jsonify([])

        allowed_exts = set()
        if ftype == 'image':
            allowed_exts = IMAGE_EXTS
        elif ftype == 'video':
            allowed_exts = VIDEO_EXTS
        else:
            allowed_exts = IMAGE_EXTS | VIDEO_EXTS

        results = []
        seen = set()
        for root, dirs, files in os.walk(DISK_SEARCH_FOLDER):
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in allowed_exts:
                    continue
                if query not in fname.lower():
                    continue
                filepath = os.path.join(root, fname)
                if filepath in seen:
                    continue
                seen.add(filepath)

                # Buscar o registrar en BD
                img = Image.query.filter_by(filepath=filepath).first()
                if not img:
                    folder_name = os.path.relpath(root, DISK_SEARCH_FOLDER)
                    if folder_name == '.':
                        folder_name = os.path.basename(DISK_SEARCH_FOLDER)
                    img = Image(filename=fname, filepath=filepath, folder=folder_name, active=True)
                    db.session.add(img)
                    db.session.commit()

                mime, _ = mimetypes.guess_type(filepath)
                is_vid = bool(mime and mime.startswith('video/'))
                results.append({
                    'id': img.id,
                    'filename': img.filename,
                    'folder': img.folder or '',
                    'is_video': is_vid,
                    'from_disk': True
                })
                if len(results) >= 20:
                    break
            if len(results) >= 20:
                break

        return jsonify(results)

    @bp.route('/search')
    @login_required
    def search_images():
        query = request.args.get('q', '').strip()
        ftype = request.args.get('type', 'all')
        if not query:
            return jsonify([])

        base_q = Image.query.filter(
            db.or_(
                Image.filename.ilike(f'%{query}%'),
                Image.folder.ilike(f'%{query}%')
            )
        ).filter_by(active=True)

        images = base_q.limit(40).all()

        def _mime_is_video(img):
            mime, _ = mimetypes.guess_type(img.filepath or img.filename)
            return bool(mime and mime.startswith('video/'))

        if ftype == 'image':
            images = [i for i in images if not _mime_is_video(i)]
        elif ftype == 'video':
            images = [i for i in images if _mime_is_video(i)]

        return jsonify([{
            'id': img.id,
            'filename': img.filename,
            'folder': img.folder or '',
            'is_video': _mime_is_video(img)
        } for img in images[:20]])
