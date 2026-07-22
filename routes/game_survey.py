from flask import jsonify, session, request
from models import db, SurveyResponse, AppConfig
from utils import get_session_id


def register_game_survey_routes(bp):
    
    @bp.route('/survey/skip', methods=['POST'])
    def survey_skip():
        uid = get_session_id()
        cfg = AppConfig.query.filter_by(key='survey_trigger').first()
        trigger = int(cfg.value) if cfg and cfg.value else 40
        session['survey_ptrigger'] = trigger
        return jsonify(success=True)

    @bp.route('/survey/submit', methods=['POST'])
    def survey_submit():
        uid = get_session_id()
        data = request.get_json() or {}
        for qid, answer in data.get('answers', {}).items():
            ans = str(answer).strip()
            if ans:
                existing = SurveyResponse.query.filter_by(user_session=uid, question_id=int(qid)).first()
                if not existing:
                    db.session.add(SurveyResponse(user_session=uid, question_id=int(qid), answer=ans))
        db.session.commit()
        return jsonify(success=True)
