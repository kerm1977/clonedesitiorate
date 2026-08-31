"""
Auto-likes background task.
Adds 2-3 likes per minute (randomly every 20-30 s) to random weekly-story
comments until the cumulative total reaches MAX_TOTAL_LIKES.
"""

import random
import threading
import time
import uuid
from werkzeug.security import generate_password_hash

MAX_LIKES_PER_COMMENT = 1000   # Cada comentario llega hasta este máximo
_threads = []
_stop_event = threading.Event()
_socketio = None
_app = None


def _set_deps(app, socketio):
    global _socketio, _app
    _app = app
    _socketio = socketio


def _image_auto_like_loop():
    from models import Image, ImageVote, User, db

    while not _stop_event.is_set():
        _stop_event.wait(180)  # cada 3 minutos
        if _stop_event.is_set():
            break

        try:
            with _app.app_context():
                images = Image.query.with_entities(Image.id).all()
                ids = [i.id for i in images]
                if not ids:
                    continue

                batch = random.sample(ids, min(40, len(ids)))

                # Dos usuarios automáticos por lote para permitir 1 o 2 likes por imagen
                u1 = User(
                    email=f'autolike_{uuid.uuid4().hex[:12]}@local',
                    password_hash=generate_password_hash('auto')
                )
                u2 = User(
                    email=f'autolike_{uuid.uuid4().hex[:12]}@local',
                    password_hash=generate_password_hash('auto')
                )
                db.session.add_all([u1, u2])
                db.session.flush()

                votes = []
                for image_id in batch:
                    add = random.choice([1, 2])
                    chosen = random.sample([u1, u2], add)
                    for u in chosen:
                        votes.append(ImageVote(image_id=image_id, user_id=u.id, vote_type='like'))

                db.session.bulk_save_objects(votes)
                db.session.commit()
        except Exception:
            import traceback
            traceback.print_exc()
            try:
                db.session.rollback()
            except Exception:
                pass


def _auto_like_loop():
    from models import WeeklyStoryComment, db

    while not _stop_event.is_set():
        # Esperar intervalo aleatorio de 120-180 segundos (≈ 0.5 likes/min)
        interval = random.uniform(120, 180)
        _stop_event.wait(interval)
        if _stop_event.is_set():
            break

        try:
            with _app.app_context():
                base_query = WeeklyStoryComment.query.filter(
                    WeeklyStoryComment.likes_count < MAX_LIKES_PER_COMMENT
                )

                count = base_query.count()
                if count == 0:
                    # Todos llegaron a 1000 — detener
                    break

                offset = random.randint(0, count - 1)
                comment = base_query.offset(offset).first()
                if not comment:
                    continue

                comment.likes_count = (comment.likes_count or 0) + 1
                new_count = comment.likes_count
                comment_id = comment.id
                db.session.commit()

                # Emitir actualización en tiempo real
                if _socketio:
                    _socketio.emit('like_update', {
                        'comment_id': comment_id,
                        'comment_type': 'weekly',
                        'likes_count': new_count
                    })
        except Exception:
            pass  # No interrumpir el loop por errores puntuales


def start_auto_likes(app, socketio):
    global _threads
    # Evitar doble inicio (ej. Flask debug reloader)
    if _threads and any(t.is_alive() for t in _threads):
        return
    _set_deps(app, socketio)
    _stop_event.clear()
    _threads = [
        threading.Thread(target=_auto_like_loop, daemon=True, name='auto_likes_comments'),
        threading.Thread(target=_image_auto_like_loop, daemon=True, name='auto_likes_images')
    ]
    for t in _threads:
        t.start()


def stop_auto_likes():
    _stop_event.set()
