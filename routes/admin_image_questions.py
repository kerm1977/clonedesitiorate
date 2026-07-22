from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, ImageQuestion, ImageQuestionResponse, Image

admin_image_questions_bp = Blueprint('admin_image_questions', __name__, url_prefix='/admin')


def _guard():
    return not current_user.is_authenticated or not current_user.is_superuser


@admin_image_questions_bp.route('/image-questions', methods=['GET', 'POST'])
@login_required
def image_questions():
    if _guard():
        return redirect(url_for('game.index'))
    
    if request.method == 'POST':
        image_id = request.form.get('image_id')
        question = request.form.get('question', '').strip()
        trigger_rating = request.form.get('trigger_rating', '200')
        
        if not image_id or not question:
            flash('Imagen y pregunta son requeridos', 'error')
            return redirect(url_for('admin_image_questions.image_questions'))
        
        db.session.add(ImageQuestion(
            image_id=int(image_id),
            question=question,
            trigger_rating=int(trigger_rating)
        ))
        db.session.commit()
        flash('Pregunta agregada a la imagen', 'success')
        return redirect(url_for('admin_image_questions.image_questions'))
    
    questions = (db.session.query(ImageQuestion, Image)
                 .join(Image, Image.id == ImageQuestion.image_id)
                 .order_by(ImageQuestion.created_at.desc())
                 .all())
    images = Image.query.filter_by(active=True).order_by(Image.created_at.desc()).all()
    images_json = [{'id': img.id, 'filename': img.filename} for img in images]
    
    return render_template('admin_image_questions.html', 
                          questions=questions, 
                          images=images,
                          images_json=images_json)


@admin_image_questions_bp.route('/image-questions/<int:question_id>/delete', methods=['POST'])
@login_required
def delete_image_question(question_id):
    if _guard():
        return redirect(url_for('game.index'))
    ImageQuestionResponse.query.filter_by(question_id=question_id).delete()
    db.session.delete(ImageQuestion.query.get_or_404(question_id))
    db.session.commit()
    flash('Pregunta eliminada', 'success')
    return redirect(url_for('admin_image_questions.image_questions'))


@admin_image_questions_bp.route('/image-questions/<int:question_id>/responses')
@login_required
def image_question_responses(question_id):
    if _guard():
        return jsonify(error='No autorizado'), 403
    question = ImageQuestion.query.get_or_404(question_id)
    responses = ImageQuestionResponse.query.filter_by(question_id=question_id).order_by(ImageQuestionResponse.created_at.desc()).all()
    return jsonify({
        'question': question.question,
        'image_id': question.image_id,
        'responses': [{
            'id': r.id,
            'answer': r.answer,
            'user_session': r.user_session,
            'created_at': r.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for r in responses]
    })
