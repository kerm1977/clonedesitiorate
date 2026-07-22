import os
from flask import Blueprint, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Image, ImageSource
from utils import scan_folder, scan_all_sources, IMAGE_EXTENSIONS
from PIL import Image

admin_media_bp = Blueprint('admin_media', __name__, url_prefix='/admin/media')


def _guard():
    return not current_user.is_authenticated or not current_user.is_superuser


@admin_media_bp.route('/sources/add', methods=['POST'])
@login_required
def add_source():
    if _guard():
        return redirect(url_for('game.index'))
    name = request.form.get('name', '').strip()
    stype = request.form.get('source_type', 'folder')
    path = request.form.get('path', '').strip()
    if not name:
        flash('El nombre es requerido', 'error')
        return redirect(url_for('admin.admin') + '#tabImagenes')
    if stype == 'upload':
        base = os.path.join(current_app.root_path, 'uploads')
        path = os.path.join(base, secure_filename(name) or 'subidas')
        os.makedirs(path, exist_ok=True)
    db.session.add(ImageSource(name=name, source_type=stype, path=path))
    db.session.commit()
    if stype == 'folder' and path:
        added, err = scan_folder(path)
        flash(f'Error: {err}' if err else f'"{name}" agregada — {added} imagen(es) nueva(s).',
              'error' if err else 'success')
    else:
        flash(f'Fuente "{name}" creada. Ahora puedes subir imágenes.', 'success')
    return redirect(url_for('admin.admin') + '#tabImagenes')


@admin_media_bp.route('/sources/<int:sid>/delete', methods=['POST'])
@login_required
def del_source(sid):
    if _guard():
        return redirect(url_for('game.index'))
    db.session.delete(ImageSource.query.get_or_404(sid))
    db.session.commit()
    flash('Fuente eliminada', 'success')
    return redirect(url_for('admin.admin') + '#tabImagenes')


@admin_media_bp.route('/sources/<int:sid>/toggle', methods=['POST'])
@login_required
def toggle_source(sid):
    if _guard():
        return jsonify(error='No autorizado'), 403
    src = ImageSource.query.get_or_404(sid)
    src.active = not src.active
    db.session.commit()
    return jsonify(active=src.active)


@admin_media_bp.route('/sources/<int:sid>/scan', methods=['POST'])
@login_required
def scan_source(sid):
    if _guard():
        return redirect(url_for('game.index'))
    src = ImageSource.query.get_or_404(sid)
    added, err = scan_folder(src.path)
    flash(f'Error: {err}' if err else f'{added} imagen(es) nueva(s) de "{src.name}".',
          'error' if err else 'success')
    return redirect(url_for('admin.admin') + '#tabImagenes')


@admin_media_bp.route('/scan-all', methods=['POST'])
@login_required
def scan_all():
    if _guard():
        return redirect(url_for('game.index'))
    total, err = scan_all_sources()
    flash(f'Error: {err}' if err else f'Escaneo completo — {total} imagen(es) nueva(s).',
          'error' if err else 'success')
    return redirect(url_for('admin.admin') + '#tabImagenes')


@admin_media_bp.route('/upload', methods=['POST'])
@login_required
def upload_images():
    if _guard():
        return redirect(url_for('game.index'))
    sid = request.form.get('source_id', '').strip()
    files = request.files.getlist('images')
    if not sid or not files:
        flash('Selecciona fuente e imágenes', 'error')
        return redirect(url_for('admin.admin') + '#tabImagenes')
    src = ImageSource.query.get_or_404(int(sid))
    os.makedirs(src.path, exist_ok=True)
    added = 0
    for f in files:
        ext = os.path.splitext(f.filename)[1].lower() if f.filename else ''
        if f and ext in IMAGE_EXTENSIONS:
            fn = secure_filename(f.filename)
            fp = os.path.normpath(os.path.join(src.path, fn))
            f.save(fp)
            if not Image.query.filter_by(filepath=fp).first():
                db.session.add(Image(filename=fn, filepath=fp, folder=src.path))
                added += 1
    db.session.commit()
    flash(f'{added} imagen(es) subida(s) a "{src.name}"', 'success')
    return redirect(url_for('admin.admin') + '#tabImagenes')


@admin_media_bp.route('/images/reset-all', methods=['POST'])
@login_required
def reset_images():
    if _guard():
        return redirect(url_for('game.index'))
    if request.form.get('confirm_word', '').strip().upper() != 'BORRAR':
        flash('Confirmación incorrecta. Escribe BORRAR para eliminar.', 'error')
        return redirect(url_for('admin.admin') + '#tabImagenes')
    upload_base = os.path.normpath(os.path.join(current_app.root_path, 'uploads'))
    images = Image.query.all()
    deleted_files = 0
    for img in images:
        fp = os.path.normpath(img.filepath) if img.filepath else ''
        if fp.startswith(upload_base) and os.path.isfile(fp):
            try:
                os.remove(fp)
                deleted_files += 1
            except Exception:
                pass
    Rating.query.delete()
    Image.query.delete()
    db.session.commit()
    flash(f'Se eliminaron {len(images)} imágenes ({deleted_files} archivos físicos) y todas sus calificaciones.', 'success')
    return redirect(url_for('admin.admin') + '#tabImagenes')


@admin_media_bp.route('/images/<int:iid>/toggle', methods=['POST'])
@login_required
def toggle_image(iid):
    if _guard():
        return jsonify(error='No autorizado'), 403
    img = Image.query.get_or_404(iid)
    img.active = not img.active
    db.session.commit()
    return jsonify(active=img.active)


@admin_media_bp.route('/compress', methods=['POST'])
@login_required
def compress_images():
    if _guard():
        return redirect(url_for('game.index'))
    
    folder_path = request.form.get('folder_path', '').strip()
    quality = int(request.form.get('quality', 75))
    max_width = int(request.form.get('max_width', 1920))
    
    if not folder_path or not os.path.isdir(folder_path):
        flash('La carpeta no existe o no es accesible', 'error')
        return redirect(url_for('admin.admin') + '#tabImagenes')
    
    compressed = 0
    errors = []
    log = []
    
    for fn in os.listdir(folder_path):
        ext = os.path.splitext(fn)[1].lower()
        if ext in {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}:
            fp = os.path.normpath(os.path.join(folder_path, fn))
            try:
                with Image.open(fp) as img:
                    original_size = os.path.getsize(fp) / 1024  # KB
                    
                    # Convertir a RGB si es RGBA o tiene transparencia
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    
                    # Redimensionar si es necesario
                    resized = False
                    if img.width > max_width:
                        ratio = max_width / img.width
                        new_height = int(img.height * ratio)
                        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                        resized = True
                    
                    # Guardar con calidad reducida
                    output_ext = '.jpg'  # Convertir todo a JPEG para mejor compresión
                    output_fn = os.path.splitext(fn)[0] + output_ext
                    output_fp = os.path.normpath(os.path.join(folder_path, output_fn))
                    
                    # Si el archivo original es diferente al output, eliminar el original
                    if fp != output_fp and os.path.exists(fp):
                        os.remove(fp)
                    
                    img.save(output_fp, 'JPEG', quality=quality, optimize=True)
                    
                    new_size = os.path.getsize(output_fp) / 1024  # KB
                    savings = ((original_size - new_size) / original_size * 100) if original_size > 0 else 0
                    
                    compressed += 1
                    log.append(f'✓ {fn} ({original_size:.1f}KB → {new_size:.1f}KB, {savings:.1f}% reducción)')
            except Exception as e:
                errors.append(f'{fn}: {str(e)}')
                log.append(f'✗ {fn}: {str(e)}')
    
    # Guardar log en sesión para mostrar en el template
    from flask import session
    session['compress_log'] = log
    
    if errors:
        flash(f'Comprimidas {compressed} imágenes. Errores: {"; ".join(errors[:5])}', 'warning')
    else:
        flash(f'{compressed} imágenes comprimidas exitosamente', 'success')
    
    return redirect(url_for('admin.admin') + '#tabImagenes')
