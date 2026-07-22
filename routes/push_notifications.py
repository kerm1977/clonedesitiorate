from flask import Blueprint, request, jsonify
from flask_login import current_user
from models import db, PushSubscription
from utils import get_session_id
import json
import os

push_bp = Blueprint('push', __name__, url_prefix='/push')

_push_socketio = None

def set_push_socketio(sio):
    global _push_socketio
    _push_socketio = sio


@push_bp.route('/subscribe', methods=['POST'])
def subscribe():
    """Suscribir un dispositivo a notificaciones push"""
    data = request.get_json()
    user_session = get_session_id()
    
    if not data or 'endpoint' not in data or 'keys' not in data:
        return jsonify({'error': 'Datos de suscripción inválidos'}), 400
    
    # Eliminar suscripción anterior si existe
    PushSubscription.query.filter_by(user_session=user_session).delete()
    
    # Crear nueva suscripción
    uname = current_user.username if current_user.is_authenticated else None
    subscription = PushSubscription(
        user_session=user_session,
        username=uname,
        endpoint=data['endpoint'],
        p256dh=data['keys']['p256dh'],
        auth=data['keys']['auth']
    )
    db.session.add(subscription)
    db.session.commit()
    
    return jsonify({'success': True})


@push_bp.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    """Cancelar suscripción a notificaciones push"""
    user_session = get_session_id()
    PushSubscription.query.filter_by(user_session=user_session).delete()
    db.session.commit()
    return jsonify({'success': True})


@push_bp.route('/call-nita', methods=['POST'])
def call_nita():
    """Superusuario llama a nitalaosita: push + socket"""
    if not current_user.is_authenticated or not current_user.is_superuser:
        return jsonify({'error': 'No autorizado'}), 403

    # Emitir socket si está online
    if _push_socketio:
        _push_socketio.emit('call_nita', {}, to='user_nitalaosita')

    # Enviar push notification a suscripciones de nitalaosita
    subs = PushSubscription.query.filter_by(username='nitalaosita').all()
    sent = 0
    if subs:
        from push_helper import send_push_notification
        vapid_file = 'vapid_keys.json'
        if os.path.exists(vapid_file):
            with open(vapid_file, 'r') as f:
                keys = json.load(f)
            payload = json.dumps({'type': 'call', 'title': '\ud83d\udcf2 Te llaman', 'body': '\u00a1El admin quiere tu atención!'})
            for sub in subs:
                if send_push_notification(sub, payload, keys['private_key']):
                    sent += 1

    return jsonify({'ok': True, 'push_sent': sent})


@push_bp.route('/vapid-public-key')
def vapid_public_key():
    """Obtener la clave pública VAPID para el frontend"""
    vapid_file = 'vapid_keys.json'
    if os.path.exists(vapid_file):
        with open(vapid_file, 'r') as f:
            keys = json.load(f)
            return jsonify({'publicKey': keys['public_key']})
    return jsonify({'error': 'Claves VAPID no encontradas'}), 404
