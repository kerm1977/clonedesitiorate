from flask import render_template, request, redirect, url_for, session, flash, jsonify, make_response
from flask_login import current_user
from models import db, Image, Favorite, FinalFeedback, AppConfig, WeeklyStoryComment, StoryComment, CommentRead, ImageComment, Message, ImageQuestion
from utils import get_session_id


def register_game_routes(bp):
    
    @bp.route('/welcome')
    def welcome():
        return redirect(url_for('game.index'))

    @bp.route('/clear-name', methods=['POST'])
    def clear_name():
        session.pop('player_name', None)
        return redirect(url_for('game.index'))

    @bp.route('/set-name', methods=['POST'])
    def set_name():
        name = request.form.get('name', '').strip()
        if name:
            session['player_name'] = name
            session.permanent = True
        return redirect(url_for('game.index'))

    def _set_no_cache(resp):
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
        return resp

    @bp.route('/')
    def index():
        if not current_user.is_authenticated:
            return _set_no_cache(make_response(render_template('login.html')))
        return redirect(url_for('coleccion.index'))

    @bp.route('/images')
    def get_images():
        page = request.args.get('page', 1, type=int)
        per_page = 30
        
        images = Image.query.filter_by(active=True).order_by(db.func.random()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        result = {
            'images': [{
                'id': img.id,
                'url': url_for('game.serve_image', image_id=img.id),
                'thumb_url': url_for('game.serve_thumbnail', image_id=img.id) if not img.is_video else url_for('game.serve_image', image_id=img.id),
                'download_url': url_for('game.download_image', image_id=img.id),
                'filename': img.filename,
                'is_video': img.is_video
            } for img in images.items],
            'has_more': images.has_next,
            'has_prev': images.has_prev,
            'total_pages': images.pages,
            'current_page': images.page
        }
        return jsonify(result)

    @bp.route('/image/<int:image_id>/info')
    def get_image_info_route(image_id):
        img = Image.query.get_or_404(image_id)
        uid = get_session_id()
        is_fav = Favorite.query.filter_by(user_session=uid, image_id=img.id).first() is not None
        img_msg = Message.query.filter_by(trigger_image_id=img.id).first()
        
        image_question = ImageQuestion.query.filter_by(
            image_id=img.id,
            active=True
        ).first()
        
        return jsonify(id=img.id, url=url_for('game.serve_image', image_id=img.id),
                       download_url=url_for('game.download_image', image_id=img.id),
                       filename=img.filename, is_favorited=is_fav,
                       is_video=img.is_video,
                       has_confetti=img.has_confetti,
                       image_message=img_msg.text if img_msg else None,
                       image_question={'id': image_question.id, 'question': image_question.question} if image_question else None)

    # ── Bienvenida Nita: check & dismiss ──────────────────────────
    @bp.route('/nita-welcome/check')
    def nita_welcome_check():
        from flask_login import current_user
        if not current_user.is_authenticated or current_user.username != 'nitalaosita':
            return jsonify(active=False)
        def _get(k, d=''):
            c = AppConfig.query.filter_by(key=k).first()
            return c.value if c else d
        active = _get('nita_welcome_active', '0') == '1'
        if not active:
            return jsonify(active=False)
        return jsonify(
            active=True,
            title=_get('nita_welcome_title', '¡Bienvenida! 💖'),
            emoji=_get('nita_welcome_emoji', '🌸'),
            msg=_get('nita_welcome_msg', '')
        )

    @bp.route('/nita-report/check')
    def nita_report_check():
        if not current_user.is_authenticated or current_user.username != 'nitalaosita':
            return jsonify(enabled=False)
        def _get(k, d=''):
            c = AppConfig.query.filter_by(key=k).first()
            return c.value if c else d
        return jsonify(
            enabled=_get('nita_report_enabled', '0') == '1',
            title=_get('nita_report_title', '¡Gracias por reportar! 🚩'),
            emoji=_get('nita_report_emoji', '🚩'),
            msg=_get('nita_report_msg', ''),
        )

    @bp.route('/nita-welcome/dismiss', methods=['POST'])
    def nita_welcome_dismiss():
        from flask_login import current_user
        if not current_user.is_authenticated or current_user.username != 'nitalaosita':
            return jsonify(ok=False), 403
        c = AppConfig.query.filter_by(key='nita_welcome_active').first()
        if c:
            c.value = '0'
            db.session.commit()
        return jsonify(ok=True)

