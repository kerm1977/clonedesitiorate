from flask import request, current_app
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room
from models import db, ChatMessage, User
from utils import costa_rica_now_str
from datetime import datetime
import threading


def _send_chat_push_async(app, username, sender_display, content, chat_type):
    """Enviar push de chat en segundo plano para no bloquear el socket."""
    try:
        with app.app_context():
            from models import PushSubscription
            from push_helper import send_push_notification
            import json
            import os

            subs = PushSubscription.query.filter_by(username=username).all()
            if not subs:
                return

            vapid_file = 'vapid_keys.json'
            if not os.path.exists(vapid_file):
                return

            with open(vapid_file, 'r') as f:
                keys = json.load(f)

            title = '💬 Nuevo mensaje'
            body = f'{sender_display}: {content[:100]}...' if len(content) > 100 else f'{sender_display}: {content}'
            payload = json.dumps({
                'type': 'chat',
                'title': title,
                'body': body,
                'sender': sender_display,
                'chat_type': chat_type
            })

            for sub in subs:
                try:
                    send_push_notification(sub, payload, keys['private_key'])
                except Exception:
                    pass
    except Exception:
        pass


# {username: sid}
_user_sids = {}

# Período de gracia para transiciones de página de nitalaosita
_nita_disconnect_timers = {}
_nita_disconnect_lock = threading.Lock()

def get_chat_room(user1, user2):
    return 'chat__' + '__'.join(sorted([user1, user2]))

def get_moderator_room():
    """Sala compartida para el chat de moderadoras"""
    return 'moderator_chat_room'

def get_display_name(user):
    if user and user.chat_alias:
        return user.chat_alias
    return user.username if user else 'Desconocido'

def register_socket_events(socketio):

    @socketio.on('connect')
    def on_connect():
        if current_user.is_authenticated:
            if current_user.username == 'nitalaosita':
                with _nita_disconnect_lock:
                    timer = _nita_disconnect_timers.pop(current_user.username, None)
                    _user_sids[current_user.username] = request.sid
                join_room(f'user_{current_user.username}')
                if timer:
                    timer.cancel()
                    # Reconexión dentro del período de gracia: no avisar desconexión
                    return
                emit('nita_activity', {
                    'type': 'connect',
                    'icon': '🟢',
                    'text': 'Se conectó',
                    'link': None,
                    'time': costa_rica_now_str()
                }, broadcast=True)
                emit('user_online', {'username': current_user.username}, broadcast=True)
                emit('online_list', {'online': list(_user_sids.keys())}, to=request.sid)
                return

            _user_sids[current_user.username] = request.sid
            # Cada usuario se une a su sala personal para recibir notificaciones directas
            join_room(f'user_{current_user.username}')
            # Notificar a todos que este usuario se conectó
            emit('user_online', {'username': current_user.username}, broadcast=True)
            # Enviar lista de usuarios online al usuario que se acaba de conectar
            emit('online_list', {'online': list(_user_sids.keys())}, to=request.sid)
            
            # Si es una moderadora, notificar a nitalaosita
            if current_user.email in ['bolita@mummy.com', 'doll@mummy.com']:
                emit('user_online', {'username': current_user.username}, to='user_nitalaosita')

    @socketio.on('disconnect')
    def on_disconnect():
        if current_user.is_authenticated:
            if current_user.username == 'nitalaosita':
                username = current_user.username
                old_sid = _user_sids.get(username)
                app = current_app._get_current_object()

                def _nita_gone():
                    with app.app_context():
                        with _nita_disconnect_lock:
                            _nita_disconnect_timers.pop(username, None)
                            if _user_sids.get(username) == old_sid:
                                _user_sids.pop(username, None)
                            else:
                                # Ya se reconectó con otro sid
                                return
                        socketio.emit('nita_disconnected', {'time': costa_rica_now_str()})
                        socketio.emit('nita_activity', {
                            'type': 'disconnect',
                            'icon': '🔴',
                            'text': 'Se desconectó',
                            'link': None,
                            'time': costa_rica_now_str()
                        })
                        socketio.emit('user_offline', {'username': username})

                with _nita_disconnect_lock:
                    _nita_disconnect_timers[username] = threading.Timer(5.0, _nita_gone)
                    _nita_disconnect_timers[username].start()
                return

            _user_sids.pop(current_user.username, None)
            emit('user_offline', {'username': current_user.username}, broadcast=True)

    @socketio.on('join_chat')
    def on_join_chat(data):
        if not current_user.is_authenticated:
            return
        partner = data.get('partner')
        chat_type = data.get('chat_type', 'private')
        if not partner:
            return
        
        # Para chat de moderadoras, usar sala compartida
        if chat_type == 'moderator':
            room = get_moderator_room()
            join_room(room)
            print(f"[SOCKET] {current_user.username} se unió a sala de moderadoras: {room}")
        else:
            room = get_chat_room(current_user.username, partner)
            join_room(room)
            print(f"[SOCKET] {current_user.username} se unió a sala privada: {room}")
        
        # Enviar lista actualizada de online al usuario que se conecta
        emit('online_list', {'online': list(_user_sids.keys())})

    @socketio.on('leave_chat')
    def on_leave_chat(data):
        if not current_user.is_authenticated:
            return
        partner = data.get('partner')
        if not partner:
            return
        room = get_chat_room(current_user.username, partner)
        leave_room(room)

    @socketio.on('send_message')
    def on_send_message(data):
        if not current_user.is_authenticated:
            return
        partner = data.get('partner')
        content = data.get('content', '').strip()
        chat_type = data.get('chat_type', 'private')  # 'private' o 'moderator'
        if not partner or not content:
            return

        current_name = current_user.username

        # Guardar en DB - lógica simplificada
        try:
            # Para chat de moderadoras, usar receiver_name='nitalaosita' o 'moderadoras'
            if chat_type == 'moderator':
                if current_name == 'nitalaosita':
                    receiver_name = 'nitalaosita'  # Para sí mismo en el chat grupal
                else:
                    receiver_name = 'nitalaosita'  # Moderadora escribiendo a nitalaosita
            else:
                receiver_name = partner

            msg = ChatMessage(
                sender_id=current_user.id,
                sender_name=current_name,
                receiver_name=receiver_name,
                content=content,
                is_read=False,
                chat_type=chat_type,
                chat_display_name=None,
                created_at=datetime.utcnow()
            )
            db.session.add(msg)
            db.session.commit()

            sender_display = get_display_name(current_user)
            
            # Preparar payload
            if chat_type == 'moderator':
                room = get_moderator_room()
            else:
                room = get_chat_room(current_name, partner)
            
            payload = {
                'id': msg.id,
                'sender': current_name,
                'display_sender': sender_display,
                'content': content,
                'time': msg.created_at.strftime('%H:%M'),
                'room': room,
                'chat_type': msg.chat_type,
            }
            
            # Emitir según el tipo de chat
            if chat_type == 'moderator':
                # Emitir a la sala compartida de moderadoras
                emit('new_message', payload, to=room)
                print(f"[SOCKET] Mensaje de moderadora enviado a sala: {room}")
                
                # Push para usuarios offline
                if current_name == 'nitalaosita':
                    # nitalaosita envía a las moderadoras
                    from models import User
                    moderators = User.query.filter(User.email.in_(['bolita@mummy.com', 'doll@mummy.com'])).all()
                    app = current_app._get_current_object()
                    for mod in moderators:
                        if mod.username not in _user_sids:
                            socketio.start_background_task(_send_chat_push_async, app, mod.username, sender_display, content, 'moderator')
                else:
                    # Moderadora envía a nitalaosita
                    if 'nitalaosita' not in _user_sids:
                        app = current_app._get_current_object()
                        socketio.start_background_task(_send_chat_push_async, app, 'nitalaosita', sender_display, content, 'moderator')
            else:
                # Chat normal
                if partner in _user_sids:
                    emit('new_message', payload, to=room)
                    emit('new_message', payload, to=f'user_{partner}')
                else:
                    app = current_app._get_current_object()
                    socketio.start_background_task(_send_chat_push_async, app, partner, sender_display, content, 'private')
            
            # Notificaciones especiales para nitalaosita
            if current_user.is_superuser and partner == 'nitalaosita':
                emit('super_message_to_nita', {
                    'from': sender_display,
                    'preview': content[:50] + ('...' if len(content) > 50 else '')
                }, to='user_nitalaosita')
            
            # Actividad de nita
            if current_name == 'nitalaosita':
                emit('nita_activity', {
                    'type': 'chat',
                    'icon': '📱',
                    'text': f'Envió un mensaje de chat: "{content[:40]}{"..." if len(content) > 40 else ""}"',
                    'link': None,
                    'time': costa_rica_now_str()
                }, broadcast=True)
        except Exception as e:
            db.session.rollback()
            emit('error', {'msg': str(e)})

    @socketio.on('message_received')
    def on_message_received(data):
        """Receptor notifica que recibió el mensaje — reenviar al sender"""
        if not current_user.is_authenticated:
            return
        msg_id = data.get('msg_id')
        sender = data.get('sender')
        if not msg_id or not sender:
            return
        # Usar la sala personal del remitente en lugar de su SID, más robusto ante reconexiones
        emit('message_status', {'msg_id': msg_id, 'status': 'received'}, to=f'user_{sender}')

    @socketio.on('message_read')
    def on_message_read(data):
        """Receptor leyó mensajes — marcar en DB y notificar a los remitentes"""
        if not current_user.is_authenticated:
            return
        partner = data.get('partner')
        chat_type = data.get('chat_type', 'private')
        if not partner:
            return
        current_name = current_user.username
        try:
            if chat_type == 'moderator':
                if current_name == 'nitalaosita' and partner == 'nitalaosita':
                    messages = ChatMessage.query.filter(
                        db.and_(
                            ChatMessage.chat_type == 'moderator',
                            ChatMessage.receiver_name == 'nitalaosita',
                            ChatMessage.sender_name != 'nitalaosita',
                            ChatMessage.is_read == False
                        )
                    ).all()
                else:
                    messages = ChatMessage.query.filter(
                        db.and_(
                            ChatMessage.chat_type == 'moderator',
                            ChatMessage.sender_name == 'nitalaosita',
                            ChatMessage.is_read == False
                        )
                    ).all()
            else:
                messages = ChatMessage.query.filter(
                    db.and_(
                        ChatMessage.chat_type == 'private',
                        ChatMessage.sender_name == partner,
                        ChatMessage.receiver_name == current_name,
                        ChatMessage.is_read == False
                    )
                ).all()

            sender_messages = {}
            for msg in messages:
                msg.is_read = True
                sender_messages.setdefault(msg.sender_name, []).append(msg.id)

            db.session.commit()

            for sender, ids in sender_messages.items():
                for msg_id in ids:
                    emit('message_status', {'msg_id': msg_id, 'status': 'read'}, to=f'user_{sender}')
        except Exception:
            db.session.rollback()

    @socketio.on('typing')
    def on_typing(data):
        if not current_user.is_authenticated:
            return
        partner = data.get('partner')
        chat_type = data.get('chat_type', 'private')
        if not partner:
            return
        if chat_type == 'moderator':
            room = get_moderator_room()
        else:
            room = get_chat_room(current_user.username, partner)
        display = get_display_name(current_user)
        emit('user_typing', {'username': current_user.username, 'display': display}, to=room, include_self=False)

    @socketio.on('stop_typing')
    def on_stop_typing(data):
        if not current_user.is_authenticated:
            return
        partner = data.get('partner')
        chat_type = data.get('chat_type', 'private')
        if not partner:
            return
        if chat_type == 'moderator':
            room = get_moderator_room()
        else:
            room = get_chat_room(current_user.username, partner)
        emit('user_stop_typing', {'username': current_user.username}, to=room, include_self=False)

    @socketio.on('get_online')
    def on_get_online():
        emit('online_list', {'online': list(_user_sids.keys())})


def send_chat_push(username, sender_display, content, chat_type):
    """Enviar notificación push por mensaje de chat cuando el usuario está offline"""
    try:
        from models import PushSubscription
        from push_helper import send_push_to_session
        import json
        import os
        
        print(f"[PUSH] Intentando enviar push a {username} de {sender_display}")
        
        # Obtener suscripciones del usuario (por username o por user_session)
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"[PUSH] Usuario {username} no encontrado")
            return
        
        # Buscar suscripciones por username (prioridad) o por user_session
        subs = PushSubscription.query.filter_by(username=username).all()
        if not subs:
            print(f"[PUSH] No hay suscripciones por username para {username}, buscando por user_session...")
            # Si no hay por username, buscar por user_session del usuario
            from utils import get_session_id
            user_session = get_session_id()
            subs = PushSubscription.query.filter_by(user_session=user_session).all()
        
        if not subs:
            print(f"[PUSH] No hay suscripciones para {username}")
            return
        
        print(f"[PUSH] Encontradas {len(subs)} suscripciones para {username}")
        
        # Cargar clave VAPID
        vapid_file = 'vapid_keys.json'
        if not os.path.exists(vapid_file):
            print(f"[PUSH] Archivo VAPID no encontrado")
            return
        
        with open(vapid_file, 'r') as f:
            keys = json.load(f)
        
        # Preparar payload
        title = '💬 Nuevo mensaje'
        body = f'{sender_display}: {content[:100]}...' if len(content) > 100 else f'{sender_display}: {content}'
        
        payload = json.dumps({
            'type': 'chat',
            'title': title,
            'body': body,
            'sender': sender_display,
            'chat_type': chat_type
        })
        
        print(f"[PUSH] Payload: {payload}")
        
        # Enviar a cada suscripción
        sent_count = 0
        for sub in subs:
            try:
                from push_helper import send_push_notification
                result = send_push_notification(sub, payload, keys['private_key'])
                if result:
                    sent_count += 1
                    print(f"[PUSH] Push enviado exitosamente a {username}")
                else:
                    print(f"[PUSH] Push falló para {username}")
            except Exception as e:
                print(f"[PUSH] Error enviando push a {username}: {e}")
        
        print(f"[PUSH] Total enviados: {sent_count}/{len(subs)}")
    except Exception as e:
        print(f"[PUSH] Error en send_chat_push: {e}")


    @socketio.on('send_admin_modal')
    def on_send_admin_modal(data):
        if not current_user.is_authenticated or not current_user.is_superuser:
            return
        message = data.get('message', '').strip()
        if not message:
            return
        sender_display = get_display_name(current_user)
        emit('admin_modal', {
            'message': message,
            'from': sender_display
        }, to='user_nitalaosita')

    @socketio.on('nita_contact')
    def on_nita_contact(data):
        if not current_user.is_authenticated:
            return
        fake_user = data.get('fake_user', '')
        if not fake_user:
            return
        emit('nita_activity', {
            'type': 'contact',
            'icon': '📱',
            'text': f'{current_user.username} ha contactado a {fake_user}',
            'link': None,
            'time': costa_rica_now_str()
        }, broadcast=True)
