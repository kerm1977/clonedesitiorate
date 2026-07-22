from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, ScheduledUserMessage, Image, User
from datetime import datetime

admin_feedback_bp = Blueprint('admin_feedback', __name__, url_prefix='/admin')


def _guard():
    return not current_user.is_authenticated or not current_user.is_superuser


@admin_feedback_bp.route('/five-star-feedback')
@login_required
def five_star_feedback():
    if _guard():
        return redirect(url_for('game.index'))
    
    feedbacks = (db.session.query(RatingFiveFeedback, Image)
                 .join(Image, Image.id == RatingFiveFeedback.image_id)
                 .order_by(RatingFiveFeedback.created_at.desc())
                 .all())
    
    return render_template('admin_five_feedback.html', feedbacks=feedbacks)


@admin_feedback_bp.route('/five-star-feedback/<int:feedback_id>/delete', methods=['POST'])
@login_required
def delete_five_feedback(feedback_id):
    if _guard():
        return jsonify(error='No autorizado'), 403
    
    feedback = RatingFiveFeedback.query.get_or_404(feedback_id)
    db.session.delete(feedback)
    db.session.commit()
    flash('Feedback eliminado', 'success')
    return redirect(url_for('admin_feedback.five_star_feedback'))


@admin_feedback_bp.route('/five-star-feedback/delete-all', methods=['POST'])
@login_required
def delete_all_five_feedback():
    if _guard():
        return jsonify(error='No autorizado'), 403
    
    RatingFiveFeedback.query.delete()
    db.session.commit()
    flash('Todos los feedbacks eliminados', 'success')
    return redirect(url_for('admin_feedback.five_star_feedback'))


@admin_feedback_bp.route('/scheduled-messages')
@login_required
def scheduled_messages():
    if _guard():
        return redirect(url_for('game.index'))
    
    messages = ScheduledUserMessage.query.order_by(ScheduledUserMessage.scheduled_at.desc()).all()
    users = User.query.all()
    
    return render_template('admin_scheduled_messages.html', messages=messages, users=users)


@admin_feedback_bp.route('/scheduled-messages/create', methods=['POST'])
@login_required
def create_scheduled_message():
    if _guard():
        return jsonify(error='No autorizado'), 403
    
    user_id = request.form.get('user_id')
    message = request.form.get('message')
    scheduled_at = request.form.get('scheduled_at')
    send_now = request.form.get('send_now') == 'true'
    
    if not user_id or not message:
        flash('Usuario y mensaje son requeridos', 'error')
        return redirect(url_for('admin_feedback.scheduled_messages'))
    
    scheduled_dt = None
    if not send_now:
        if not scheduled_at:
            flash('Fecha y hora son requeridas para mensajes programados', 'error')
            return redirect(url_for('admin_feedback.scheduled_messages'))
        try:
            scheduled_dt = datetime.strptime(scheduled_at, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Formato de fecha inválido', 'error')
            return redirect(url_for('admin_feedback.scheduled_messages'))
    
    db.session.add(ScheduledUserMessage(
        user_id=int(user_id),
        message=message,
        scheduled_at=scheduled_dt
    ))
    db.session.commit()
    
    if send_now:
        flash('Mensaje enviado inmediatamente', 'success')
    else:
        flash('Mensaje programado creado', 'success')
    return redirect(url_for('admin_feedback.scheduled_messages'))


@admin_feedback_bp.route('/scheduled-messages/<int:message_id>/delete', methods=['POST'])
@login_required
def delete_scheduled_message(message_id):
    if _guard():
        return jsonify(error='No autorizado'), 403
    
    message = ScheduledUserMessage.query.get_or_404(message_id)
    db.session.delete(message)
    db.session.commit()
    flash('Mensaje programado eliminado', 'success')
    return redirect(url_for('admin_feedback.scheduled_messages'))
