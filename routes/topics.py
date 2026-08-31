import os
import random
import uuid
import hashlib
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Topic, TopicReply, FakeUser, AdminNotification, User
from utils import log_activity
from PIL import Image as PILImage

topics_bp = Blueprint('topics', __name__, url_prefix='/temas')

UPLOAD_DIR = 'uploads/topics'
ALLOWED_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif'}


def _topic_upload_dir():
    path = os.path.join(current_app.root_path, UPLOAD_DIR)
    os.makedirs(path, exist_ok=True)
    return path


def _allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_IMAGE_EXTS


def _get_reply_display_name(current_username, form_name=None):
    nita_name = 'Nita la Osita'
    if current_username == 'nitalaosita':
        return nita_name
    if form_name and form_name != nita_name:
        fake_names = [u[0] for u in FakeUser.query.with_entities(FakeUser.name).all()]
        if form_name in fake_names:
            return form_name
    fake_names = [u[0] for u in FakeUser.query.with_entities(FakeUser.name).filter(FakeUser.name != nita_name).all()]
    if fake_names:
        return random.choice(fake_names)
    return current_username


def _notify_superusers_about_reply(topic, reply):
    admins = User.query.filter_by(is_superuser=True).all()
    for admin in admins:
        if admin.id == reply.user_id:
            continue
        notif = AdminNotification(
            recipient_id=admin.id,
            actor_id=reply.user_id,
            type='nita_topic_reply',
            topic_id=topic.id,
            reply_id=reply.id,
            message=f'Nita la Osita comentó en "{topic.title}"',
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.session.add(notif)
    db.session.commit()


@topics_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    pagination = Topic.query.order_by(Topic.published_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template('topics.html', pagination=pagination)


@topics_bp.route('/create', methods=['POST'])
@login_required
def create():
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    link = request.form.get('link', '').strip()
    image = request.files.get('image')

    if not title:
        flash('El título es obligatorio', 'warning')
        return redirect(url_for('topics.index'))

    image_path = None
    if image and image.filename:
        if not _allowed_file(image.filename):
            flash('Formato de imagen no permitido', 'warning')
            return redirect(url_for('topics.index'))

        upload_dir = _topic_upload_dir()
        original_fn = secure_filename(image.filename)
        unique_fn = f"{uuid.uuid4().hex}_{original_fn}"
        image_path = os.path.normpath(os.path.join(upload_dir, unique_fn))
        image.save(image_path)

    topic = Topic(
        user_id=current_user.id,
        title=title,
        description=description,
        link=link,
        image_path=image_path,
        published_at=datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    db.session.add(topic)
    db.session.commit()

    log_activity(current_user.username, 'topic_create', 'topic', topic.title,
                 object_url=url_for('topics.detail', topic_id=topic.id),
                 object_id=topic.id)

    flash('Tema publicado', 'success')
    return redirect(url_for('topics.detail', topic_id=topic.id))


@topics_bp.route('/<int:topic_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if not current_user.is_superuser and current_user.id != topic.user_id:
        flash('No autorizado', 'danger')
        return redirect(url_for('topics.detail', topic_id=topic.id))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        link = request.form.get('link', '').strip()
        image = request.files.get('image')

        if not title:
            flash('El título es obligatorio', 'warning')
            return redirect(url_for('topics.edit', topic_id=topic.id))

        topic.title = title
        topic.description = description
        topic.link = link

        if image and image.filename:
            if not _allowed_file(image.filename):
                flash('Formato de imagen no permitido', 'warning')
                return redirect(url_for('topics.edit', topic_id=topic.id))

            if topic.image_path and os.path.isfile(topic.image_path):
                try:
                    os.remove(topic.image_path)
                except OSError:
                    pass

            upload_dir = _topic_upload_dir()
            original_fn = secure_filename(image.filename)
            unique_fn = f"{uuid.uuid4().hex}_{original_fn}"
            image_path = os.path.normpath(os.path.join(upload_dir, unique_fn))
            image.save(image_path)
            topic.image_path = image_path

        db.session.commit()
        flash('Tema actualizado', 'success')
        return redirect(url_for('topics.detail', topic_id=topic.id))

    return render_template('topic_edit.html', topic=topic)


@topics_bp.route('/<int:topic_id>')
@login_required
def detail(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    replies = TopicReply.query.filter_by(topic_id=topic.id).order_by(TopicReply.created_at.asc()).all()
    replies = sorted(replies, key=lambda r: (0 if r.display_name == 'Nita la Osita' else 1, r.created_at))
    reply_display_name = _get_reply_display_name(current_user.username)
    return render_template('topic_detail.html', topic=topic, replies=replies, reply_display_name=reply_display_name)


@topics_bp.route('/<int:topic_id>/reply', methods=['POST'])
@login_required
def reply(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    content = request.form.get('content', '').strip()
    form_display_name = request.form.get('display_name', '').strip()

    if not content:
        flash('La respuesta no puede estar vacía', 'warning')
        return redirect(url_for('topics.detail', topic_id=topic.id))

    display_name = _get_reply_display_name(current_user.username, form_display_name)

    reply = TopicReply(
        topic_id=topic.id,
        user_id=current_user.id,
        display_name=display_name,
        content=content,
        created_at=datetime.utcnow()
    )
    db.session.add(reply)
    db.session.commit()

    log_activity(current_user.username, 'topic_reply', 'topic_reply', topic.title,
                 object_url=url_for('topics.detail', topic_id=topic.id),
                 object_id=reply.id, extra=content[:200])

    if current_user.username == 'nitalaosita':
        _notify_superusers_about_reply(topic, reply)

    flash('Respuesta agregada', 'success')
    return redirect(url_for('topics.detail', topic_id=topic.id))


@topics_bp.route('/reply/<int:reply_id>/edit', methods=['POST'])
@login_required
def edit_reply(reply_id):
    reply = TopicReply.query.get_or_404(reply_id)
    if not current_user.is_superuser and current_user.id != reply.user_id:
        flash('No autorizado', 'danger')
        return redirect(url_for('topics.index'))
    content = request.form.get('content', '').strip()
    if not content:
        flash('La respuesta no puede estar vacía', 'warning')
        return redirect(url_for('topics.detail', topic_id=reply.topic_id))

    reply.content = content
    db.session.commit()
    flash('Respuesta actualizada', 'success')
    return redirect(url_for('topics.detail', topic_id=reply.topic_id))


@topics_bp.route('/reply/<int:reply_id>/delete', methods=['POST'])
@login_required
def delete_reply(reply_id):
    reply = TopicReply.query.get_or_404(reply_id)
    if not current_user.is_superuser and current_user.id != reply.user_id:
        flash('No autorizado', 'danger')
        return redirect(url_for('topics.index'))

    topic_id = reply.topic_id
    db.session.delete(reply)
    db.session.commit()
    flash('Respuesta eliminada', 'success')
    return redirect(url_for('topics.detail', topic_id=topic_id))


@topics_bp.route('/notificacion/<int:notif_id>/leida')
@login_required
def mark_notification_read(notif_id):
    notif = AdminNotification.query.get_or_404(notif_id)
    if notif.recipient_id != current_user.id:
        flash('No autorizado', 'danger')
        return redirect(url_for('topics.index'))
    notif.is_read = True
    db.session.commit()
    if notif.topic_id:
        return redirect(url_for('topics.detail', topic_id=notif.topic_id))
    return redirect(url_for('topics.index'))


@topics_bp.route('/<int:topic_id>/delete', methods=['POST'])
@login_required
def delete_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if not current_user.is_superuser and current_user.id != topic.user_id:
        flash('No autorizado', 'danger')
        return redirect(url_for('topics.index'))

    if topic.image_path and os.path.isfile(topic.image_path):
        try:
            os.remove(topic.image_path)
        except OSError:
            pass

    db.session.delete(topic)
    db.session.commit()
    flash('Tema eliminado', 'success')
    return redirect(url_for('topics.index'))


@topics_bp.route('/<int:topic_id>/image')
@login_required
def serve_image(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if not topic.image_path or not os.path.isfile(topic.image_path):
        abort(404)
    return send_file(topic.image_path)


@topics_bp.route('/<int:topic_id>/thumb')
@login_required
def serve_thumb(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if not topic.image_path or not os.path.isfile(topic.image_path):
        abort(404)
    cache_dir = os.path.join(current_app.root_path, 'uploads', 'topics', 'thumbs')
    os.makedirs(cache_dir, exist_ok=True)
    key = hashlib.md5(topic.image_path.encode('utf-8')).hexdigest() + '_q55.webp'
    cache_path = os.path.join(cache_dir, key)
    if not os.path.exists(cache_path):
        try:
            pil_img = PILImage.open(topic.image_path)
            if pil_img.mode in ('RGBA', 'P'):
                pil_img = pil_img.convert('RGB')
            pil_img.thumbnail((600, 600), PILImage.LANCZOS)
            pil_img.save(cache_path, format='WEBP', quality=55, optimize=True, method=0)
        except Exception:
            return send_file(topic.image_path)
    response = send_file(cache_path, mimetype='image/webp', conditional=True)
    response.headers['Cache-Control'] = 'public, max-age=604800'
    return response
