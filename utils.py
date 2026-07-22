import os
import uuid
import re
from flask import session
from models import db, Image

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.mp4', '.webm', '.mov', '.avi', '.mkv'}


def convert_photobearrate_links(content):
    """
    Convierte enlaces photobearrate en texto plano a enlaces HTML clickeables
    Ejemplo: https://photobearrate.tailb81e5f.ts.net/?image_id=976
    Se convierte en: <a href="https://photobearrate.tailb81e5f.ts.net/?image_id=976" target="_blank">https://photobearrate.tailb81e5f.ts.net/?image_id=976</a>
    """
    if not content:
        return content
    
    # Patrón para detectar enlaces photobearrate
    pattern = r'(https?://photobearrate\.[a-z0-9]+\.ts\.net/\?image_id=\d+)'
    
    # Reemplazar con enlace HTML
    def replace_with_link(match):
        url = match.group(1)
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{url}</a>'
    
    return re.sub(pattern, replace_with_link, content)


def get_session_id():
    from flask_login import current_user
    # Si el usuario está autenticado, usar su user_id
    if current_user.is_authenticated:
        return f"user_{current_user.id}"
    # Si no está autenticado, usar session_id
    if 'uid' not in session:
        session['uid'] = str(uuid.uuid4())
        session.permanent = True
    return session['uid']


def scan_folder(folder_path):
    added = 0
    folder_path = os.path.normpath(folder_path)
    if not os.path.isdir(folder_path):
        return 0, 'La carpeta no existe o no es accesible'
    for fn in os.listdir(folder_path):
        if os.path.splitext(fn)[1].lower() in IMAGE_EXTENSIONS:
            fp = os.path.normpath(os.path.join(folder_path, fn))
            if not Image.query.filter_by(filepath=fp).first():
                db.session.add(Image(filename=fn, filepath=fp, folder=folder_path))
                added += 1
    db.session.commit()
    return added, None


def scan_all_sources():
    from models import ImageSource
    total, errors = 0, []
    for src in ImageSource.query.filter_by(active=True, source_type='folder').all():
        added, err = scan_folder(src.path)
        total += added
        if err:
            errors.append(f'{src.name}: {err}')
    return total, ('; '.join(errors) if errors else None)
