import eventlet
eventlet.monkey_patch()

import os
import json
import re
from flask import Flask, send_file
from sqlalchemy import text
from flask_login import LoginManager
from flask_socketio import SocketIO
from werkzeug.security import generate_password_hash
from models import db, User, AboutContent, Favorite
from utils import get_session_id

socketio = SocketIO()

# Credenciales de superusuario
SUPERUSERS = [
    {
        'email': 'bolita@mummy.com',
        'username': 'bolita',
        'password': 'CR129x7848n'
    },
    {
        'email': 'doll@mummy.com',
        'username': 'doll',
        'password': 'CR129x7848n'
    }
]


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-xK9mP2-change-in-prod')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///photogame.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.config['TEMPLATES_AUTO_RELOAD'] = True

    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins='*', async_mode='eventlet',
                      ping_timeout=60, ping_interval=1)

    @app.teardown_appcontext
    def _close_db(exc):
        db.session.remove()

    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_globals():
        from models import AppConfig
        def _cfg(k, d=''):
            try:
                c = AppConfig.query.filter_by(key=k).first()
                return c.value if c else d
            except Exception:
                return d
        return {
            'about': AboutContent.query.first(),
            'nita_report_enabled': _cfg('nita_report_enabled', '0') == '1',
            'nita_report_title': _cfg('nita_report_title', '¡Gracias por reportar! 🚩'),
            'nita_report_emoji': _cfg('nita_report_emoji', '🚩'),
            'nita_report_msg': _cfg('nita_report_msg', ''),
        }

    @app.template_filter('linkify')
    def linkify(text):
        # Convert URLs to clickable links
        url_pattern = r'(https?://[^\s<>"\'\)]+)'
        replacement = r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>'
        return re.sub(url_pattern, replacement, text)

    @app.route('/robots.txt')
    def robots_txt():
        return app.send_static_file('robots.txt')

    @app.route('/favicon.ico')
    def favicon():
        import base64, io
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==')
        return send_file(io.BytesIO(png), mimetype='image/png')

    from routes.game import game_bp
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.admin_media import admin_media_bp
    from routes.admin_connect import admin_connect_bp
    from routes.admin_messages import admin_messages_bp
    from routes.admin_survey import admin_survey_bp
    from routes.admin_users import admin_users_bp
    from routes.admin_image_questions import admin_image_questions_bp
    from routes.admin_feedback import admin_feedback_bp
    from routes.push_notifications import push_bp
    from routes.game_chat import game_chat_bp, register_game_chat_routes
    register_game_chat_routes(game_chat_bp)
    from routes.coleccion import coleccion_bp
    from routes.nita_upload import nita_upload_bp

    app.register_blueprint(game_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_media_bp)
    app.register_blueprint(admin_connect_bp)
    app.register_blueprint(admin_messages_bp)
    app.register_blueprint(admin_survey_bp)
    app.register_blueprint(admin_users_bp)
    app.register_blueprint(admin_image_questions_bp)
    app.register_blueprint(admin_feedback_bp)
    app.register_blueprint(push_bp)
    app.register_blueprint(game_chat_bp)
    app.register_blueprint(coleccion_bp)
    app.register_blueprint(nita_upload_bp)
    app.config.setdefault('MAX_CONTENT_LENGTH', 100 * 1024 * 1024)

    from chat_socket import register_socket_events
    register_socket_events(socketio)
    
    # Pasar socketio a game_chat para emitir desde rutas Flask
    from routes.game_chat import set_socketio
    set_socketio(socketio)

    # Pasar socketio a admin para bienvenida nita y otros emits
    from routes.admin import set_admin_socketio, set_chat_socketio
    set_admin_socketio(socketio)
    set_chat_socketio(socketio)

    # Pasar socketio a game_stories para emitir desde rutas Flask
    from routes.game_stories import set_stories_socketio
    set_stories_socketio(socketio)

    # Pasar socketio a auth para notificar conexión de nitalaosita
    from routes.auth import set_auth_socketio
    set_auth_socketio(socketio)

    # Pasar socketio a push para emitir call_nita
    from routes.push_notifications import set_push_socketio
    set_push_socketio(socketio)

    with app.app_context():
        db.create_all()
        _set_sqlite_pragmas()
        _run_migrations()

    # Iniciar auto-likes en background
    from auto_likes import start_auto_likes
    start_auto_likes(app, socketio)

    return app


def _run_migrations():
    cols = [
        "ALTER TABLE message ADD COLUMN label VARCHAR(100)",
        "ALTER TABLE message ADD COLUMN trigger_image_id INTEGER",
        "ALTER TABLE survey_question ADD COLUMN question_type VARCHAR(20) DEFAULT 'text'",
        "ALTER TABLE survey_question ADD COLUMN options TEXT",
        "ALTER TABLE image_source ADD COLUMN source_type VARCHAR(20) DEFAULT 'folder'",
        "ALTER TABLE weekly_story_comment ADD COLUMN likes_count INTEGER DEFAULT 0",
        "ALTER TABLE story_comment ADD COLUMN likes_count INTEGER DEFAULT 0",
        "ALTER TABLE push_subscription ADD COLUMN username VARCHAR(100)",
        "ALTER TABLE image_comment ADD COLUMN likes_count INTEGER DEFAULT 0",
    ]
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_chat_message_sender_name ON chat_message(sender_name)",
        "CREATE INDEX IF NOT EXISTS idx_chat_message_receiver_name ON chat_message(receiver_name)",
        "CREATE INDEX IF NOT EXISTS idx_chat_message_chat_type ON chat_message(chat_type)",
        "CREATE INDEX IF NOT EXISTS idx_chat_message_is_read ON chat_message(is_read)",
        "CREATE INDEX IF NOT EXISTS idx_chat_message_created_at ON chat_message(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_comment_read_user ON comment_read(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_comment_read_lookup ON comment_read(user_id, comment_type, comment_id)",
    ]
    with db.engine.connect() as conn:
        for sql in cols:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass
        for sql in indexes:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass


def _set_sqlite_pragmas():
    with db.engine.connect() as conn:
        try:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA synchronous=NORMAL"))
            conn.execute(text("PRAGMA cache_size=-64000"))
            conn.execute(text("PRAGMA temp_store=MEMORY"))
            conn.execute(text("PRAGMA foreign_keys=ON"))
            conn.commit()
        except Exception:
            pass


app = create_app()

if __name__ == '__main__':
    # Leer puerto desde config.json
    port = 8080
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                port = config.get('port', 8080)
        except Exception:
            pass
    
    with app.app_context():
        db.create_all()
        for su in SUPERUSERS:
            if not User.query.filter_by(email=su['email']).first():
                db.session.add(User(
                    email=su['email'],
                    username=su['username'],
                    password_hash=generate_password_hash(su['password']),
                    is_superuser=True
                ))
        db.session.commit()
        print('Superusuarios listos: bolita@mummy.com / doll@mummy.com  (vacavaca)')

        from seed_fake_chat_users import seed_fake_chat_users
        seed_fake_chat_users()
        print('Usuarias falsas del chat sembradas.')
    
    # Configuración SSL - Desactivado para Tailscale Funnel
    # Tailscale Funnel proporciona HTTPS con certificados válidos
    print(f'SSL local desactivado. Tailscale Funnel proporciona HTTPS.')
    print(f'Corriendo en puerto: {port}')
    
    socketio.run(app, debug=False, use_reloader=False, host='0.0.0.0', port=port)
