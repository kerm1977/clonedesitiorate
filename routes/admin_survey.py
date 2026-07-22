import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, SurveyQuestion, SurveyResponse, AppConfig

admin_survey_bp = Blueprint('admin_survey', __name__, url_prefix='/admin')


def _guard():
    return not current_user.is_authenticated or not current_user.is_superuser


@admin_survey_bp.route('/survey')
@login_required
def survey_admin():
    if _guard():
        return redirect(url_for('game.index'))
    cfg = AppConfig.query.filter_by(key='survey_trigger').first()
    trigger = int(cfg.value) if cfg and cfg.value else 40
    questions = SurveyQuestion.query.order_by(SurveyQuestion.order).all()
    responses = (db.session.query(SurveyResponse.id, SurveyQuestion.text,
                                  SurveyResponse.answer, SurveyResponse.user_session)
                 .join(SurveyQuestion, SurveyQuestion.id == SurveyResponse.question_id)
                 .order_by(SurveyResponse.user_session, SurveyQuestion.order).all())
    return render_template('admin_survey.html', trigger=trigger,
                           questions=questions, responses=responses)


@admin_survey_bp.route('/survey/config', methods=['POST'])
@login_required
def survey_config():
    if _guard():
        return redirect(url_for('game.index'))
    val = request.form.get('trigger', '40').strip()
    cfg = AppConfig.query.filter_by(key='survey_trigger').first()
    if cfg:
        cfg.value = val
    else:
        db.session.add(AppConfig(key='survey_trigger', value=val))
    db.session.commit()
    flash(f'Encuesta se activa cada {val} calificaciones', 'success')
    return redirect(url_for('admin_survey.survey_admin'))


@admin_survey_bp.route('/survey/questions/add', methods=['POST'])
@login_required
def survey_add_question():
    if _guard():
        return redirect(url_for('game.index'))
    text = request.form.get('text', '').strip()
    qtype = request.form.get('question_type', 'text')
    options_raw = request.form.get('options', '').strip()
    options_json = None
    if qtype == 'select' and options_raw:
        opts = [o.strip() for o in options_raw.split('|') if o.strip()]
        options_json = json.dumps(opts, ensure_ascii=False)
    if text:
        count = SurveyQuestion.query.count()
        db.session.add(SurveyQuestion(text=text, order=count,
                                      question_type=qtype, options=options_json))
        db.session.commit()
        flash('Pregunta agregada', 'success')
    return redirect(url_for('admin_survey.survey_admin'))


@admin_survey_bp.route('/survey/questions/<int:qid>/delete', methods=['POST'])
@login_required
def survey_del_question(qid):
    if _guard():
        return redirect(url_for('game.index'))
    SurveyResponse.query.filter_by(question_id=qid).delete()
    db.session.delete(SurveyQuestion.query.get_or_404(qid))
    db.session.commit()
    flash('Pregunta eliminada', 'success')
    return redirect(url_for('admin_survey.survey_admin'))


@admin_survey_bp.route('/survey/questions/<int:qid>/toggle', methods=['POST'])
@login_required
def survey_toggle_question(qid):
    if _guard():
        return redirect(url_for('game.index'))
    q = SurveyQuestion.query.get_or_404(qid)
    q.active = not q.active
    db.session.commit()
    return jsonify(active=q.active)


@admin_survey_bp.route('/survey/responses/delete-all', methods=['POST'])
@login_required
def survey_del_all_responses():
    if _guard():
        return redirect(url_for('game.index'))
    SurveyResponse.query.delete()
    db.session.commit()
    flash('Todas las respuestas eliminadas', 'success')
    return redirect(url_for('admin_survey.survey_admin'))


@admin_survey_bp.route('/survey/responses/<int:rid>/delete', methods=['POST'])
@login_required
def survey_del_response(rid):
    if _guard():
        return redirect(url_for('game.index'))
    db.session.delete(SurveyResponse.query.get_or_404(rid))
    db.session.commit()
    return jsonify(success=True)
