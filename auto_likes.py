"""
Auto-likes background task.
Adds 2-3 likes per minute (randomly every 20-30 s) to random weekly-story
comments until the cumulative total reaches MAX_TOTAL_LIKES.
"""

import random
import threading
import time

MAX_LIKES_PER_COMMENT = 1000   # Cada comentario llega hasta este máximo
_thread = None
_stop_event = threading.Event()
_socketio = None
_app = None


def _set_deps(app, socketio):
    global _socketio, _app
    _app = app
    _socketio = socketio


def _auto_like_loop():
    from models import WeeklyStoryComment, db

    while not _stop_event.is_set():
        # Esperar intervalo aleatorio de 20-30 segundos (≈ 2-3 likes/min)
        interval = random.uniform(20, 30)
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
    global _thread
    # Evitar doble inicio (ej. Flask debug reloader)
    if _thread and _thread.is_alive():
        return
    _set_deps(app, socketio)
    _stop_event.clear()
    _thread = threading.Thread(target=_auto_like_loop, daemon=True, name='auto_likes')
    _thread.start()


def stop_auto_likes():
    _stop_event.set()
