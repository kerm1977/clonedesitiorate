from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from flask_socketio import emit
from models import db, ChatMessage, User
from utils import get_session_id
from chat_socket import get_chat_room, get_display_name, _user_sids
import os
import uuid
import time
from werkzeug.utils import secure_filename

# Variable global para socketio (se asigna desde app.py)
_socketio = None

def set_socketio(socketio_instance):
    global _socketio
    _socketio = socketio_instance

game_chat_bp = Blueprint('game_chat', __name__)

# Diccionario en memoria para rastrear quién está escribiendo
# {username: {partner: timestamp}}
_typing_status = {}

# Diccionario para rastrear usuarios online
# {username: last_seen_timestamp}
_online_users = {}

def register_game_chat_routes(bp):
    
    @bp.route('/chat/messages/<username>', methods=['GET'])
    @login_required
    def get_chat_messages(username):
        uid = get_session_id()
        current_name = current_user.username if current_user.is_authenticated else None
        chat_type = request.args.get('chat_type', 'private')  # 'private' o 'moderator'
        
        # Lógica especial para nitalaosita - simplificada
        if current_name == 'nitalaosita':
            if chat_type == 'moderator':
                # Chat de moderadoras: mostrar todos los mensajes de tipo moderator donde nitalaosita participa
                messages = ChatMessage.query.filter(
                    db.and_(
                        ChatMessage.chat_type == 'moderator',
                        db.or_(
                            ChatMessage.sender_name == 'nitalaosita',
                            ChatMessage.receiver_name == 'nitalaosita'
                        )
                    )
                ).order_by(ChatMessage.created_at.asc()).all()
                
                print(f"DEBUG: nitalaosita moderator chat - found {len(messages)} messages")
            else:
                # Chat privado normal
                messages = ChatMessage.query.filter(
                    db.or_(
                        db.and_(
                            ChatMessage.sender_name == 'nitalaosita',
                            ChatMessage.receiver_name == username,
                            ChatMessage.chat_type == chat_type
                        ),
                        db.and_(
                            ChatMessage.receiver_name == 'nitalaosita',
                            ChatMessage.sender_name == username,
                            ChatMessage.chat_type == chat_type
                        )
                    )
                ).order_by(ChatMessage.created_at.asc()).all()
        elif current_user.is_superuser and username == 'nitalaosita' and chat_type == 'moderator':
            # Superusuario viendo chat de moderadoras con nitalaosita - simplificado
            messages = ChatMessage.query.filter(
                db.and_(
                    ChatMessage.chat_type == 'moderator',
                    db.or_(
                        ChatMessage.sender_name == 'nitalaosita',
                        ChatMessage.receiver_name == 'nitalaosita'
                    )
                )
            ).order_by(ChatMessage.created_at.asc()).all()
            
            print(f"DEBUG: superuser moderator chat - found {len(messages)} messages")
        else:
            # Para otros usuarios, chat directo con el nombre especificado
            messages = ChatMessage.query.filter(
                db.or_(
                    db.and_(
                        ChatMessage.receiver_name == username,
                        ChatMessage.sender_name == current_name,
                        ChatMessage.chat_type == chat_type
                    ),
                    db.and_(
                        ChatMessage.sender_name == username,
                        ChatMessage.receiver_name == current_name,
                        ChatMessage.chat_type == chat_type
                    )
                )
            ).order_by(ChatMessage.created_at.asc()).all()
        
        # Obtener el nombre de display del chat (si existe)
        display_name = None
        # Para nitalaosita, usar nombres fijos según el tipo de chat
        if current_name == 'nitalaosita':
            if chat_type == 'moderator':
                display_name = 'Chat con moderadoras'
            else:
                partner = User.query.filter_by(username=username).first()
                if partner:
                    display_name = partner.chat_alias if partner.chat_alias else partner.username
        elif current_user.is_superuser and username == 'nitalaosita' and chat_type == 'moderator':
            display_name = 'Chat de moderadoras'
        elif messages:
            display_name = messages[0].chat_display_name
        
        # Cargar todos los remitentes de una vez para evitar consultas N+1
        sender_ids = [m.sender_id for m in messages if m.sender_id]
        senders = {}
        if sender_ids:
            senders = {u.id: u for u in User.query.filter(User.id.in_(sender_ids)).all()}

        messages_data = []
        for m in messages:
            is_me = (m.sender_name == current_name) or (m.sender_id == current_user.id if current_user.is_authenticated else False)

            # Obtener alias del remitente si existe
            sender_alias = None
            sender = senders.get(m.sender_id) if m.sender_id else None
            if sender and sender.chat_alias:
                sender_alias = sender.chat_alias

            # Determinar el nombre a mostrar
            if display_name and not is_me:
                display_sender_name = display_name
            elif sender_alias:
                display_sender_name = sender_alias
            else:
                display_sender_name = m.sender_name
            
            messages_data.append({
                'id': m.id,
                'sender_name': m.sender_name,
                'display_sender_name': display_sender_name,
                'content': m.content,
                'image_path': m.image_path,
                'created_at': m.created_at.strftime('%H:%M'),
                'is_me': is_me
            })
        
        return jsonify({
            'messages': messages_data,
            'display_name': display_name
        })
    
    @bp.route('/chat/send', methods=['POST'])
    @login_required
    def send_chat_message():
        uid = get_session_id()
        current_name = current_user.username if current_user.is_authenticated else None
        receiver_name = request.form.get('receiver_name', '').strip()
        content = request.form.get('content', '').strip()
        chat_display_name = request.form.get('chat_display_name', '').strip()
        chat_type = request.form.get('chat_type', 'private')  # 'private' o 'moderator'
        
        if not receiver_name or not content:
            return jsonify(error='Datos incompletos'), 400
        
        # Solo superusuarios pueden establecer un nombre personalizado del chat
        if chat_display_name and not current_user.is_superuser:
            return jsonify(error='Solo superusuarios pueden personalizar el nombre del chat'), 400
        
        # Lógica especial para nitalaosita
        if current_name == 'nitalaosita':
            # nitalaosita envía a superusuarios
            if chat_type == 'moderator':
                # Chat de moderadoras: enviar a bolita y doll
                # Crear un solo mensaje con receiver_name especial para evitar duplicados
                msg = ChatMessage(
                    sender_id=current_user.id,
                    sender_name=current_name,
                    receiver_id=None,  # No receiver específico
                    receiver_name='moderadoras',  # Nombre especial para identificar
                    content=content,
                    chat_type=chat_type,
                    is_read=False
                )
                db.session.add(msg)
                db.session.commit()
                
                # Notificar a ambas moderadoras via Socket.IO
                moderators = User.query.filter(User.email.in_(['bolita@mummy.com', 'doll@mummy.com'])).all()
                if _socketio:
                    for moderator in moderators:
                        _socketio.emit('new_message', {
                            'id': msg.id,
                            'sender_name': current_name,
                            'receiver_name': moderator.username,
                            'content': content,
                            'image_path': None,
                            'created_at': msg.created_at.isoformat(),
                            'is_read': False
                        }, to=f'user_{moderator.username}')
                
                return jsonify(success=True, message_id=msg.id)
            else:
                # Chat privado: enviar al superusuario especificado
                superuser = User.query.filter_by(username=receiver_name).first()
                if not superuser:
                    return jsonify(error='Superusuario no encontrado'), 400
                
                msg = ChatMessage(
                    sender_id=current_user.id,
                    sender_name=current_name,
                    receiver_id=superuser.id,
                    receiver_name=receiver_name,
                    content=content,
                    chat_type=chat_type,
                    is_read=False
                )
        elif receiver_name == 'nitalaosita' and current_user.is_superuser:
            # Superusuario envía a nitalaosita
            receiver = User.query.filter_by(username='nitalaosita').first()
            if not receiver:
                return jsonify(error='Usuario no encontrado'), 400
            
            msg = ChatMessage(
                sender_id=current_user.id,
                sender_name=current_name,
                receiver_id=receiver.id,
                receiver_name=receiver_name,
                content=content,
                chat_type=chat_type,
                is_read=False
            )
        else:
            # Para otros usuarios, envío directo
            msg = ChatMessage(
                sender_id=current_user.id if current_user.is_authenticated else None,
                sender_session=uid if not current_user.is_authenticated else None,
                sender_name=current_name,
                receiver_name=receiver_name,
                content=content,
                chat_type=chat_type,
                is_read=False
            )
        
        # Si es superusuario y proporcionó un nombre personalizado, usarlo
        if current_user.is_superuser and chat_display_name:
            msg.chat_display_name = chat_display_name
            
            # Actualizar todos los mensajes existentes del chat con el mismo nombre personalizado
            ChatMessage.query.filter(
                db.or_(
                    db.and_(
                        ChatMessage.receiver_name == receiver_name,
                        ChatMessage.sender_name == current_name
                    ),
                    db.and_(
                        ChatMessage.sender_name == receiver_name,
                        ChatMessage.receiver_name == current_name
                    )
                )
            ).update({'chat_display_name': chat_display_name})
        
        db.session.add(msg)
        db.session.commit()
        
        return jsonify(success=True, message_id=msg.id)
    
    @bp.route('/chat/users', methods=['GET'])
    @login_required
    def get_users():
        current_name = current_user.username if current_user.is_authenticated else None
        query = request.args.get('q', '').strip()
        chat_type = request.args.get('chat_type', 'private')  # 'private' o 'moderator'
        
        # Lógica especial para nitalaosita: mostrar sus chats activos
        if current_name == 'nitalaosita':
            # Si es chat de moderadora, solo mostrar bolita@mummy.com
            if chat_type == 'moderator':
                bolita = User.query.filter_by(email='bolita@mummy.com').first()
                if bolita:
                    return jsonify([{
                        'id': bolita.id,
                        'username': bolita.username,
                        'display_name': bolita.chat_alias if bolita.chat_alias else bolita.username,
                        'is_superuser': bolita.is_superuser
                    }])
                return jsonify([])
            
            # Para chat privado, mostrar superusuarios
            superusers = User.query.filter_by(is_superuser=True).all()
            users = []
            for su in superusers:
                users.append({
                    'id': su.id,
                    'username': su.username,
                    'display_name': su.chat_alias if su.chat_alias else su.username,
                    'is_superuser': su.is_superuser
                })
            
            if query:
                users = [u for u in users if query.lower() in (u['display_name'] or u['username']).lower()]
            
            return jsonify(users)
        
        # Para superusuarios, siempre mostrar usuarios especiales
        users = []
        if current_user.is_superuser:
            # nitalaosita
            nitalaosita = User.query.filter_by(username='nitalaosita').first()
            if nitalaosita:
                users.append({
                    'id': nitalaosita.id,
                    'username': nitalaosita.username,
                    'is_superuser': nitalaosita.is_superuser
                })
            
            # doll@mummy.com (Danita)
            doll = User.query.filter_by(email='doll@mummy.com').first()
            if doll:
                users.append({
                    'id': doll.id,
                    'username': doll.chat_alias if doll.chat_alias else doll.username,
                    'is_superuser': doll.is_superuser
                })
            
            # bolita@mummy.com (pedomom67)
            bolita = User.query.filter_by(email='bolita@mummy.com').first()
            if bolita:
                users.append({
                    'id': bolita.id,
                    'username': bolita.chat_alias if bolita.chat_alias else bolita.username,
                    'is_superuser': bolita.is_superuser
                })
        
        if not query:
            return jsonify(users)
        
        # Buscar usuarios por nombre de usuario
        search_users = User.query.filter(
            User.username.ilike(f'%{query}%')
        ).limit(20).all()
        
        # Combinar resultados sin duplicados
        existing_ids = {u['id'] for u in users}
        for u in search_users:
            if u.id not in existing_ids:
                users.append({
                    'id': u.id,
                    'username': u.username,
                    'is_superuser': u.is_superuser
                })
        
        return jsonify(users)
    
    @bp.route('/chat/clear/<username>', methods=['POST'])
    @login_required
    def clear_chat(username):
        current_name = current_user.username if current_user.is_authenticated else None
        chat_type = request.args.get('chat_type', 'private')  # 'private' o 'moderator'
        
        # Fuerza bruta para superusuarios eliminando chat de moderadoras
        if current_user.is_superuser and username == 'nitalaosita' and chat_type == 'moderator':
            # Eliminar TODOS los mensajes con chat_type='moderator' sin filtros
            ChatMessage.query.filter(ChatMessage.chat_type == 'moderator').delete(synchronize_session=False)
            db.session.commit()
            
            # Notificar a nitalaosita y a las moderadoras
            if _socketio:
                from models import User
                moderators = User.query.filter(User.email.in_(['bolita@mummy.com', 'doll@mummy.com'])).all()
                for mod in moderators:
                    _socketio.emit('chat_cleared', {'by': current_name, 'partner': username, 'chat_type': chat_type}, to=f'user_{mod.username}')
                _socketio.emit('chat_cleared', {'by': current_name, 'partner': username, 'chat_type': chat_type}, to='user_nitalaosita')
            
            return jsonify(success=True)
        
        # Lógica especial para nitalaosita - simplificada
        if current_name == 'nitalaosita':
            if chat_type == 'moderator':
                # Eliminar todos los mensajes de tipo moderator donde nitalaosita participa
                ChatMessage.query.filter(
                    db.and_(
                        ChatMessage.chat_type == 'moderator',
                        db.or_(
                            ChatMessage.sender_name == 'nitalaosita',
                            ChatMessage.receiver_name == 'nitalaosita'
                        )
                    )
                ).delete(synchronize_session=False)
            else:
                # Eliminar mensajes del chat privado con el usuario especificado
                ChatMessage.query.filter(
                    db.or_(
                        db.and_(
                            ChatMessage.sender_name == 'nitalaosita',
                            ChatMessage.receiver_name == username,
                            ChatMessage.chat_type == chat_type
                        ),
                        db.and_(
                            ChatMessage.receiver_name == 'nitalaosita',
                            ChatMessage.sender_name == username,
                            ChatMessage.chat_type == chat_type
                        )
                    )
                ).delete(synchronize_session=False)
        else:
            # Para otros usuarios, eliminar mensajes del chat directo con chat_type
            ChatMessage.query.filter(
                db.or_(
                    db.and_(
                        ChatMessage.receiver_name == username,
                        ChatMessage.sender_name == current_name,
                        ChatMessage.chat_type == chat_type
                    ),
                    db.and_(
                        ChatMessage.sender_name == username,
                        ChatMessage.receiver_name == current_name,
                        ChatMessage.chat_type == chat_type
                    )
                )
            ).delete()
        
        db.session.commit()

        # Notificar al partner en tiempo real para que actualice su vista
        if _socketio:
            if chat_type == 'moderator' and (current_user.is_superuser or current_name == 'nitalaosita'):
                # Para chat de moderadoras, notificar a nitalaosita y a las moderadoras
                from models import User
                moderators = User.query.filter(User.email.in_(['bolita@mummy.com', 'doll@mummy.com'])).all()
                for mod in moderators:
                    _socketio.emit('chat_cleared', {'by': current_name, 'partner': username, 'chat_type': chat_type}, to=f'user_{mod.username}')
                _socketio.emit('chat_cleared', {'by': current_name, 'partner': username, 'chat_type': chat_type}, to='user_nitalaosita')
            else:
                # Para chats normales, notificar al room y al usuario
                room = get_chat_room(current_name, username)
                _socketio.emit('chat_cleared', {'by': current_name, 'partner': username, 'chat_type': chat_type}, to=room)
                _socketio.emit('chat_cleared', {'by': current_name, 'partner': username, 'chat_type': chat_type}, to=f'user_{username}')

        return jsonify(success=True)
    
    @bp.route('/chat/send-image', methods=['POST'])
    @login_required
    def send_chat_image():
        uid = get_session_id()
        current_name = current_user.username if current_user.is_authenticated else None
        receiver_name = request.form.get('receiver_name', '').strip()
        chat_display_name = request.form.get('chat_display_name', '').strip()
        chat_type = request.form.get('chat_type', 'private')  # 'private' o 'moderator'
        
        if 'image' not in request.files:
            return jsonify(error='No se proporcionó archivo'), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify(error='No se seleccionó archivo'), 400
        
        if not receiver_name:
            return jsonify(error='Datos incompletos'), 400
        
        # Validar imagen o video
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'mov', 'webm', 'avi', 'mkv'}
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if ext not in allowed_extensions:
            return jsonify(error='Formato no permitido'), 400
        
        # Crear directorio de chat si no existe
        chat_dir = os.path.join('static', 'chat_images')
        os.makedirs(chat_dir, exist_ok=True)
        
        # Generar nombre único
        unique_filename = f"{uuid.uuid4().hex}.{ext}"
        image_path = os.path.join(chat_dir, unique_filename)
        file.save(image_path)
        
        # Lógica especial para nitalaosita
        if current_name == 'nitalaosita':
            if chat_type == 'moderator':
                # Chat de moderadoras: enviar a bolita y doll
                # Crear un solo mensaje con receiver_name='moderadoras' para evitar duplicados
                msg = ChatMessage(
                    sender_id=current_user.id,
                    sender_name=current_name,
                    receiver_id=None,
                    receiver_name='moderadoras',
                    image_path=f'/static/chat_images/{unique_filename}',
                    chat_type=chat_type,
                    is_read=False
                )
            else:
                # Chat privado: enviar al superusuario especificado
                superuser = User.query.filter_by(username=receiver_name).first()
                if not superuser:
                    return jsonify(error='Superusuario no encontrado'), 400
                
                msg = ChatMessage(
                    sender_id=current_user.id,
                    sender_name=current_name,
                    receiver_id=superuser.id,
                    receiver_name=receiver_name,
                    image_path=f'/static/chat_images/{unique_filename}',
                    chat_type=chat_type
                )
        elif receiver_name == 'nitalaosita' and current_user.is_superuser:
            receiver = User.query.filter_by(username='nitalaosita').first()
            if not receiver:
                return jsonify(error='Usuario no encontrado'), 400
            
            msg = ChatMessage(
                sender_id=current_user.id,
                sender_name=current_name,
                receiver_id=receiver.id,
                receiver_name=receiver_name,
                image_path=f'/static/chat_images/{unique_filename}',
                chat_type=chat_type,
                is_read=False
            )
        else:
            msg = ChatMessage(
                sender_id=current_user.id if current_user.is_authenticated else None,
                sender_session=uid if not current_user.is_authenticated else None,
                sender_name=current_name,
                receiver_name=receiver_name,
                image_path=f'/static/chat_images/{unique_filename}',
                chat_type=chat_type,
                is_read=False
            )
        
        db.session.add(msg)
        db.session.commit()
        
        # Emitir evento Socket.IO para que el receptor vea la imagen en tiempo real
        if _socketio:
            sender_display = get_display_name(current_user)
            
            # Lógica especial para chat de moderadoras
            if chat_type == 'moderator':
                if current_name == 'nitalaosita':
                    # nitalaosita envía a las moderadoras
                    moderators = User.query.filter(User.email.in_(['bolita@mummy.com', 'doll@mummy.com'])).all()
                    for moderator in moderators:
                        room = get_chat_room(current_name, moderator.username)
                        payload = {
                            'id': msg.id,
                            'sender': current_name,
                            'display_sender': sender_display,
                            'content': None,
                            'image_path': msg.image_path,
                            'time': msg.created_at.strftime('%H:%M'),
                            'room': room,
                            'chat_type': msg.chat_type,
                        }
                        _socketio.emit('new_message', payload, to=room)
                        _socketio.emit('new_message', payload, to=f'user_{moderator.username}')
                else:
                    # Moderadora envía a nitalaosita
                    room = get_chat_room(current_name, receiver_name)
                    payload = {
                        'id': msg.id,
                        'sender': current_name,
                        'display_sender': sender_display,
                        'content': None,
                        'image_path': msg.image_path,
                        'time': msg.created_at.strftime('%H:%M'),
                        'room': room,
                        'chat_type': msg.chat_type,
                    }
                    _socketio.emit('new_message', payload, to='user_nitalaosita')
                    _socketio.emit('new_message', payload, to=room)
            else:
                # Lógica normal para otros casos
                room = get_chat_room(current_name, receiver_name)
                payload = {
                    'id': msg.id,
                    'sender': current_name,
                    'display_sender': sender_display,
                    'content': None,
                    'image_path': msg.image_path,
                    'time': msg.created_at.strftime('%H:%M'),
                    'room': room,
                    'chat_type': msg.chat_type,
                }
                _socketio.emit('new_message', payload, to=room)
                _socketio.emit('new_message', payload, to=f'user_{receiver_name}')
        
        return jsonify(success=True, message_id=msg.id)
    
    @bp.route('/chat/delete-message/<int:msg_id>', methods=['POST'])
    @login_required
    def delete_chat_message(msg_id):
        msg = ChatMessage.query.get_or_404(msg_id)
        current_name = current_user.username

        # Puede borrar: el sender, el receiver, o nitalaosita
        is_involved = (msg.sender_name == current_name or msg.receiver_name == current_name
                       or msg.sender_id == current_user.id or msg.receiver_id == current_user.id
                       or current_name == 'nitalaosita')
        if not is_involved:
            return jsonify(error='No autorizado'), 403

        partner = msg.receiver_name if msg.sender_name == current_name else msg.sender_name

        # Si nitalaosita elimina un mensaje en chat de moderadoras, eliminar todos los mensajes relacionados
        if current_name == 'nitalaosita' and msg.chat_type == 'moderator':
            # Buscar y eliminar todos los mensajes con el mismo contenido y timestamp
            related_messages = ChatMessage.query.filter(
                db.and_(
                    ChatMessage.sender_name == msg.sender_name,
                    ChatMessage.content == msg.content,
                    ChatMessage.chat_type == 'moderator',
                    ChatMessage.created_at == msg.created_at
                )
            ).all()
            
            for related_msg in related_messages:
                # Borrar archivo de imagen del disco si existe
                if related_msg.image_path:
                    disk_path = related_msg.image_path.lstrip('/')
                    if os.path.exists(disk_path):
                        try:
                            os.remove(disk_path)
                        except Exception:
                            pass
                db.session.delete(related_msg)
        else:
            # Borrar archivo de imagen del disco si existe
            if msg.image_path:
                disk_path = msg.image_path.lstrip('/')
                if os.path.exists(disk_path):
                    try:
                        os.remove(disk_path)
                    except Exception:
                        pass
            db.session.delete(msg)

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify(error=f'Error al eliminar mensaje: {str(e)}'), 500

        # Notificar en tiempo real a ambos usuarios
        if _socketio:
            room = get_chat_room(current_name, partner)
            _socketio.emit('message_deleted', {'msg_id': msg_id}, to=room)
            _socketio.emit('message_deleted', {'msg_id': msg_id}, to=f'user_{partner}')

        return jsonify(success=True)

    @bp.route('/chat/edit-message/<int:msg_id>', methods=['POST'])
    @login_required
    def edit_chat_message(msg_id):
        msg = ChatMessage.query.get_or_404(msg_id)
        current_name = current_user.username

        # Solo el sender puede editar su mensaje
        is_sender = (msg.sender_name == current_name or msg.sender_id == current_user.id)
        if not is_sender:
            return jsonify(error='No autorizado'), 403

        new_content = request.json.get('content', '').strip() if request.is_json else request.form.get('content', '').strip()
        if not new_content:
            return jsonify(error='Contenido vacío'), 400

        # Actualizar el mensaje
        msg.content = new_content
        msg.edited = True
        msg.edited_at = db.func.now()

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify(error=f'Error al editar mensaje: {str(e)}'), 500

        # Notificar en tiempo real al partner
        partner = msg.receiver_name if msg.sender_name == current_name else msg.sender_name
        if _socketio:
            room = get_chat_room(current_name, partner)
            _socketio.emit('message_edited', {
                'msg_id': msg_id,
                'content': new_content,
                'edited': True
            }, to=room)
            _socketio.emit('message_edited', {
                'msg_id': msg_id,
                'content': new_content,
                'edited': True
            }, to=f'user_{partner}')

        return jsonify(success=True, content=new_content)

    @bp.route('/chat/clear-all', methods=['POST'])
    @login_required
    def clear_all_chats():
        if not current_user.is_superuser:
            return jsonify(error='No autorizado'), 403

        try:
            ChatMessage.query.delete(synchronize_session=False)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            import traceback; traceback.print_exc()
            return jsonify(error=str(e)), 500

        # Emitir a cada usuario online por su sala personal
        if _socketio:
            for username in list(_user_sids.keys()):
                _socketio.emit('all_chats_cleared', {}, to=f'user_{username}')

        return jsonify(success=True)
    
    @bp.route('/chat/unread-count', methods=['GET'])
    @login_required
    def get_unread_count():
        current_name = current_user.username if current_user.is_authenticated else None
        
        # Lógica especial para nitalaosita
        if current_name == 'nitalaosita':
            # Contar mensajes no leídos de superusuarios
            superusers = User.query.filter_by(is_superuser=True).all()
            superuser_ids = [su.id for su in superusers]
            
            unread_count = ChatMessage.query.filter(
                db.and_(
                    ChatMessage.receiver_name == 'nitalaosita',
                    ChatMessage.sender_id.in_(superuser_ids),
                    ChatMessage.is_read == False
                )
            ).count()
        else:
            # Para otros usuarios, contar mensajes no leídos donde son receiver
            unread_count = ChatMessage.query.filter(
                db.and_(
                    ChatMessage.receiver_name == current_name,
                    ChatMessage.is_read == False
                )
            ).count()
        
        return jsonify({'unread_count': unread_count})
    
    @bp.route('/chat/heartbeat', methods=['POST'])
    @login_required
    def heartbeat():
        current_name = current_user.username if current_user.is_authenticated else None
        if current_name:
            _online_users[current_name] = time.time()
        return jsonify(success=True)
    
    @bp.route('/chat/online', methods=['GET'])
    @login_required
    def get_online_users():
        now = time.time()
        online = [u for u, ts in _online_users.items() if (now - ts) < 90]
        return jsonify({'online': online})
    
    @bp.route('/chat/typing', methods=['POST'])
    @login_required
    def set_typing():
        current_name = current_user.username if current_user.is_authenticated else None
        partner = request.json.get('partner') if request.is_json else request.form.get('partner')
        if current_name and partner:
            if current_name not in _typing_status:
                _typing_status[current_name] = {}
            _typing_status[current_name][partner] = time.time()
        return jsonify(success=True)
    
    @bp.route('/chat/get-alias', methods=['GET'])
    @login_required
    def get_chat_alias():
        current_name = current_user.username if current_user.is_authenticated else None
        if not current_name:
            return jsonify(success=False, error='No autenticado'), 401
        
        try:
            user = User.query.filter_by(username=current_name).first()
            if user:
                return jsonify(success=True, alias=user.chat_alias)
            return jsonify(success=False, error='Usuario no encontrado'), 404
        except Exception as e:
            return jsonify(success=False, error=str(e)), 500
    
    @bp.route('/chat/set-alias', methods=['POST'])
    @login_required
    def set_chat_alias():
        current_name = current_user.username if current_user.is_authenticated else None
        if not current_name:
            return jsonify(success=False, error='No autenticado'), 401
        
        alias = request.json.get('alias', '').strip() if request.is_json else request.form.get('alias', '').strip()
        
        try:
            user = User.query.filter_by(username=current_name).first()
            if user:
                user.chat_alias = alias if alias else None
                db.session.commit()
                return jsonify(success=True, alias=alias)
            return jsonify(success=False, error='Usuario no encontrado'), 404
        except Exception as e:
            db.session.rollback()
            return jsonify(success=False, error=str(e)), 500
    
    @bp.route('/chat/set-partner-alias', methods=['POST'])
    @login_required
    def set_partner_alias():
        # Guardar el alias personalizado para un partner específico (para nitalaosita)
        if not current_user.is_authenticated:
            return jsonify(success=False, error='No autenticado'), 401
        
        # Solo permitir a nitalaosita usar esta función
        if current_user.username != 'nitalaosita':
            return jsonify(success=False, error='No autorizado'), 403
        
        partner = request.json.get('partner', '').strip() if request.is_json else request.form.get('partner', '').strip()
        alias = request.json.get('alias', '').strip() if request.is_json else request.form.get('alias', '').strip()
        
        if not partner or not alias:
            return jsonify(success=False, error='Datos incompletos'), 400
        
        try:
            # Usar el campo chat_display_name del modelo ChatMessage para guardar el alias
            # Buscamos si ya existe un mensaje con este partner para actualizar el alias
            from models import ChatMessage
            # Guardar el alias en el campo chat_display_name de los mensajes futuros
            # Para simplificar, usaremos una variable de sesión o simplemente retornamos éxito
            # El frontend ya maneja mostrar el alias
            return jsonify(success=True, alias=alias)
        except Exception as e:
            return jsonify(success=False, error=str(e)), 500
    
    @bp.route('/chat/typing/<partner>', methods=['GET'])
    @login_required
    def get_typing(partner):
        # Comprobar si el partner está escribiéndole al usuario actual
        current_name = current_user.username if current_user.is_authenticated else None
        is_typing = False
        if partner in _typing_status:
            ts = _typing_status[partner].get(current_name, 0)
            is_typing = (time.time() - ts) < 4  # 4 segundos de ventana
        return jsonify({'is_typing': is_typing, 'partner': partner})
    
    @bp.route('/chat/mark-read/<username>', methods=['POST'])
    @login_required
    def mark_chat_read(username):
        current_name = current_user.username if current_user.is_authenticated else None
        
        # Lógica especial para nitalaosita
        if current_name == 'nitalaosita':
            # Marcar como leídos los mensajes de superusuarios
            superusers = User.query.filter_by(is_superuser=True).all()
            superuser_ids = [su.id for su in superusers]
            
            ChatMessage.query.filter(
                db.and_(
                    ChatMessage.receiver_name == 'nitalaosita',
                    ChatMessage.sender_id.in_(superuser_ids),
                    ChatMessage.is_read == False
                )
            ).update({'is_read': True})
        else:
            # Para otros usuarios, marcar como leídos los mensajes del chat
            ChatMessage.query.filter(
                db.and_(
                    db.or_(
                        ChatMessage.receiver_name == username,
                        ChatMessage.sender_name == username
                    ),
                    ChatMessage.is_read == False
                )
            ).update({'is_read': True})
        
        db.session.commit()
        return jsonify(success=True)
