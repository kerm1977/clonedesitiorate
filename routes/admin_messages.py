import json
from io import BytesIO
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from models import db, Message

admin_messages_bp = Blueprint('admin_messages', __name__, url_prefix='/admin')


def _guard():
    return not current_user.is_authenticated or not current_user.is_superuser


@admin_messages_bp.route('/messages', methods=['POST'])
@login_required
def add_message():
    if _guard():
        return redirect(url_for('game.index'))
    txt = request.form.get('text', '').strip()
    label = request.form.get('label', '').strip() or None
    tid = request.form.get('trigger_image_id', '').strip()
    trigger_image_id = int(tid) if tid.isdigit() else None
    if txt:
        db.session.add(Message(text=txt, label=label, trigger_image_id=trigger_image_id))
        db.session.commit()
        flash('Mensaje agregado', 'success')
    return redirect(url_for('admin.admin') + '#tabMensajes')


@admin_messages_bp.route('/messages/<int:mid>/delete', methods=['POST'])
@login_required
def del_message(mid):
    if _guard():
        return redirect(url_for('game.index'))
    db.session.delete(Message.query.get_or_404(mid))
    db.session.commit()
    flash('Mensaje eliminado', 'success')
    return redirect(url_for('admin.admin') + '#tabMensajes')


@admin_messages_bp.route('/messages/export')
@login_required
def export_messages():
    if _guard():
        return redirect(url_for('game.index'))
    msgs = [{'text': m.text} for m in Message.query.order_by(Message.created_at).all()]
    data = json.dumps(msgs, ensure_ascii=False, indent=2)
    buf = BytesIO(data.encode('utf-8'))
    buf.seek(0)
    return send_file(buf, mimetype='application/json',
                     as_attachment=True, download_name='mensajes_photobearrate.json')


@admin_messages_bp.route('/messages/import', methods=['POST'])
@login_required
def import_messages():
    if _guard():
        return redirect(url_for('game.index'))
    f = request.files.get('json_file')
    if not f or not f.filename.endswith('.json'):
        flash('Selecciona un archivo .json válido', 'error')
        return redirect(url_for('admin.admin'))
    try:
        data = json.loads(f.read().decode('utf-8'))
        if not isinstance(data, list):
            raise ValueError('El JSON debe ser una lista [ {...}, ... ]')
        added = 0
        for item in data:
            text = item.get('text', '').strip() if isinstance(item, dict) else str(item).strip()
            if text:
                db.session.add(Message(text=text))
                added += 1
        db.session.commit()
        flash(f'Se importaron {added} mensajes ✅', 'success')
    except Exception as exc:
        flash(f'Error al importar: {exc}', 'error')
    return redirect(url_for('admin.admin'))
