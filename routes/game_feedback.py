from flask import request, jsonify, redirect, url_for, flash
from models import db, FinalFeedback, ImageQuestionResponse, ScheduledUserMessage
from utils import get_session_id
from datetime import datetime
from flask_login import current_user


def register_game_feedback_routes(bp):
    
    @bp.route('/feedback', methods=['POST'])
    def submit_feedback():
        uid = get_session_id()
        comment = request.form.get('comment', '').strip()
        if comment and not FinalFeedback.query.filter_by(user_session=uid).first():
            db.session.add(FinalFeedback(user_session=uid, comment=comment))
            db.session.commit()
        flash('¡Gracias por tu comentario! 💜', 'success')
        return redirect(url_for('game.index'))

    @bp.route('/image-question/answer', methods=['POST'])
    def answer_image_question():
        uid = get_session_id()
        data = request.get_json()
        question_id = data.get('question_id')
        answer = data.get('answer', '').strip()
        
        if not question_id:
            return jsonify(error='Datos inválidos'), 400
        
        existing = ImageQuestionResponse.query.filter_by(
            question_id=question_id,
            user_session=uid
        ).first()
        
        if existing:
            return jsonify(error='Ya respondida'), 400
        
        if answer:
            db.session.add(ImageQuestionResponse(
                question_id=question_id,
                user_session=uid,
                answer=answer
            ))
            db.session.commit()
        
        return jsonify(success=True)

    @bp.route('/five-feedback/submit', methods=['POST'])
    def submit_five_feedback():
        # Rating system removed - this endpoint is disabled
        return jsonify(success=True)

    @bp.route('/scheduled-message/respond', methods=['POST'])
    def respond_scheduled_message():
        if not current_user.is_authenticated:
            return jsonify(error='No autorizado'), 403
        
        data = request.get_json()
        message_id = data.get('message_id')
        response = data.get('response', '').strip()
        
        if not message_id:
            return jsonify(error='Datos inválidos'), 400
        
        message = ScheduledUserMessage.query.get_or_404(message_id)
        
        if message.user_id != current_user.id:
            return jsonify(error='No autorizado'), 403
        
        message.response = response
        message.responded_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify(success=True)
