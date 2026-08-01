import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Image
from PIL import Image as PILImage

nita_upload_bp = Blueprint('nita_upload', __name__, url_prefix='/nita-upload')

COLECCION_FOLDER = r'E:\coleccion'
ALLOWED_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif'}
ALLOWED_VIDEO_EXTS = {'.mp4', '.webm', '.mov', '.avi', '.mkv'}
ALLOWED_UPLOAD_EXTS = ALLOWED_IMAGE_EXTS | ALLOWED_VIDEO_EXTS


def _is_nita_or_superuser():
    return current_user.is_authenticated and (current_user.is_superuser or current_user.username in ['nita', 'lausita', 'nitalaosita'])


@nita_upload_bp.route('', methods=['POST'])
@login_required
def upload():
    if not _is_nita_or_superuser():
        return jsonify(error='No autorizado'), 403

    if 'file' not in request.files:
        return jsonify(error='No se envió archivo'), 400

    f = request.files['file']
    destination = request.form.get('destination', 'images')
    if f.filename == '':
        return jsonify(error='No se seleccionó archivo'), 400

    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTS:
        return jsonify(error='Tipo de archivo no permitido'), 400

    is_video = ext in ALLOWED_VIDEO_EXTS
    original_fn = secure_filename(f.filename)
    unique_fn = f"{uuid.uuid4().hex}_{original_fn}"

    if destination == 'coleccion':
        os.makedirs(COLECCION_FOLDER, exist_ok=True)
        save_path = os.path.normpath(os.path.join(COLECCION_FOLDER, unique_fn))
        f.save(save_path)
        return jsonify(success=True, filename=unique_fn, destination='coleccion')

    # default: images (save to uploads/nita_uploads and add to Image model)
    upload_dir = os.path.join(current_app.root_path, 'uploads', 'nita_uploads')
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.normpath(os.path.join(upload_dir, unique_fn))
    f.save(save_path)

    # Generate thumbnail for images
    thumb_path = None
    if not is_video:
        try:
            thumb_dir = os.path.join(current_app.root_path, 'uploads', 'nita_thumbs')
            os.makedirs(thumb_dir, exist_ok=True)
            thumb_fn = f"{uuid.uuid4().hex}.webp"
            thumb_path = os.path.join(thumb_dir, thumb_fn)
            pil_img = PILImage.open(save_path)
            if pil_img.mode in ('RGBA', 'P'):
                pil_img = pil_img.convert('RGB')
            pil_img.thumbnail((320, 320), PILImage.LANCZOS)
            pil_img.save(thumb_path, 'WEBP', quality=60)
        except Exception:
            thumb_path = None

    img = Image(filename=unique_fn, filepath=save_path, folder=upload_dir, active=True)
    db.session.add(img)
    db.session.commit()

    return jsonify(success=True, image_id=img.id, filename=unique_fn, destination='images', is_video=is_video)
