from flask import request, jsonify, render_template, session, Response
from flask_login import current_user, login_required
from models import db, Story, WeeklyStory, WeeklyStoryComment, StoryComment, CommentRead, CommentLike, ImageComment
from datetime import datetime
from utils import get_session_id, costa_rica_now_str, log_activity
import re

_socketio = None

def set_stories_socketio(socketio_instance):
    global _socketio
    _socketio = socketio_instance

def register_game_stories_routes(bp):
    
    @bp.route('/stories/save', methods=['POST'])
    def save_story():
        """Guarda una historia nueva"""
        try:
            data = request.get_json()
            title = data.get('title', '').strip()
            content = data.get('content', '').strip()
            
            if not title or not content:
                return jsonify({'error': 'El título y el contenido son obligatorios'}), 400
            
            user_session = get_session_id()
            if not user_session:
                return jsonify({'error': 'Sesión no válida'}), 400
            
            # Convertir enlaces photobearrate a HTML
            from utils import convert_photobearrate_links
            content = convert_photobearrate_links(content)
            
            story = Story(
                user_session=user_session,
                title=title,
                content=content
            )
            db.session.add(story)
            db.session.commit()
            
            return jsonify({'success': True, 'story_id': story.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/stories')
    def list_stories():
        """Muestra todas las historias del usuario"""
        user_session = get_session_id()
        if not user_session:
            return "Sesión no válida", 400
        
        stories = Story.query.filter_by(user_session=user_session).order_by(Story.created_at.desc()).all()
        
        # Marcar comentarios como leídos para nitalaosita
        if current_user.is_authenticated and current_user.username == 'nitalaosita':
            for story in stories:
                for comment in story.comments:
                    if not CommentRead.query.filter_by(
                        user_id=current_user.id,
                        comment_type='story',
                        comment_id=comment.id
                    ).first():
                        read_record = CommentRead(
                            user_id=current_user.id,
                            comment_type='story',
                            comment_id=comment.id
                        )
                        db.session.add(read_record)
            db.session.commit()
        
        return render_template('stories.html', stories=stories)
    
    @bp.route('/stories/<int:story_id>')
    def view_story(story_id):
        """Muestra una historia específica"""
        user_session = get_session_id()
        if not user_session:
            return "Sesión no válida", 400
        
        story = Story.query.filter_by(id=story_id, user_session=user_session).first_or_404()
        return render_template('story_detail.html', story=story)
    
    @bp.route('/stories/<int:story_id>/delete', methods=['POST'])
    def delete_story(story_id):
        """Elimina una historia"""
        try:
            user_session = get_session_id()
            if not user_session:
                return jsonify({'error': 'Sesión no válida'}), 400
            
            story = Story.query.filter_by(id=story_id, user_session=user_session).first_or_404()
            db.session.delete(story)
            db.session.commit()
            
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/stories/<int:story_id>/download')
    def download_story(story_id):
        """Descarga una historia como archivo TXT"""
        user_session = get_session_id()
        if not user_session:
            return "Sesión no válida", 400
        
        story = Story.query.filter_by(id=story_id, user_session=user_session).first_or_404()
        
        # Convertir HTML a texto plano
        text_content = re.sub(r'<[^>]+>', '\n', story.content)
        text_content = re.sub(r'\n\s*\n', '\n\n', text_content)
        text_content = text_content.strip()
        
        txt_content = f"{story.title}\n{'=' * len(story.title)}\n\n{text_content}\n\nCreado: {story.created_at.strftime('%d/%m/%Y %H:%M')}"
        
        response = Response(
            txt_content,
            mimetype='text/plain',
            headers={
                'Content-Disposition': f'attachment; filename="{story.title}.txt"'
            }
        )
        return response
    
    @bp.route('/weekly-story')
    def weekly_story():
        """Muestra la historia de la semana activa"""
        from datetime import datetime, timedelta
        today = datetime.utcnow()
        week_start = today - timedelta(days=today.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        story = WeeklyStory.query.filter_by(active=True).order_by(WeeklyStory.week_start.desc()).first()
        comments = []
        user_likes = set()
        if story:
            comments = WeeklyStoryComment.query.filter_by(weekly_story_id=story.id).order_by(WeeklyStoryComment.created_at.desc()).all()
            
            # Marcar comentarios como leídos para nitalaosita
            if current_user.is_authenticated and current_user.username == 'nitalaosita':
                for comment in comments:
                    if not CommentRead.query.filter_by(
                        user_id=current_user.id,
                        comment_type='weekly',
                        comment_id=comment.id
                    ).first():
                        read_record = CommentRead(
                            user_id=current_user.id,
                            comment_type='weekly',
                            comment_id=comment.id
                        )
                        db.session.add(read_record)
                db.session.commit()
            
            # Cargar likes del usuario actual
            if current_user.is_authenticated and (current_user.is_superuser or current_user.username == 'nitalaosita'):
                user_likes_db = CommentLike.query.filter_by(
                    user_id=current_user.id,
                    comment_type='weekly'
                ).all()
                user_likes = {like.comment_id for like in user_likes_db}
        
        return render_template('weekly_story.html', story=story, comments=comments, user_likes=user_likes)
    
    @bp.route('/weekly-story/<int:story_id>/comment', methods=['POST'])
    def add_weekly_comment(story_id):
        """Agrega un comentario a la historia de la semana"""
        try:
            story = WeeklyStory.query.get_or_404(story_id)
            content = request.form.get('content', '').strip()
            
            if not content:
                return jsonify({'error': 'El comentario es obligatorio'}), 400
            
            # Validar que story_id sea válido
            if not story_id or story_id is None:
                return jsonify({'error': 'ID de historia inválido'}), 400
            
            # Si el usuario está logueado
            if current_user.is_authenticated:
                # Si es superusuario, usar el nombre que escribió
                if current_user.is_superuser:
                    username = request.form.get('username', '').strip()
                    if not username:
                        return jsonify({'error': 'El nombre es obligatorio'}), 400
                else:
                    # Usuario normal, usar su username automáticamente
                    username = current_user.username
                user_id = current_user.id
                user_session = None
            else:
                # No logueado, usar el nombre que escribió
                username = request.form.get('username', '').strip()
                user_id = None
                user_session = get_session_id()
                if not username:
                    return jsonify({'error': 'El nombre es obligatorio'}), 400
            
            comment = WeeklyStoryComment(
                weekly_story_id=story_id,
                user_id=user_id,
                user_session=user_session,
                username=username,
                content=content
            )
            db.session.add(comment)
            db.session.commit()
            
            log_activity(username, 'comment', 'weekly_comment', story.title or 'Historia de la semana',
                         object_url='/weekly-story#comentarios',
                         object_id=comment.id,
                         extra=content)
            
            # Notificar actividad de nitalaosita
            if username == 'nitalaosita' and _socketio:
                _socketio.emit('nita_activity', {
                    'type': 'comment',
                    'icon': '💬',
                    'text': f'Comentó en la historia: "{content[:50]}{"..." if len(content) > 50 else ""}"',
                    'link': '/weekly-story#comentarios',
                    'time': costa_rica_now_str()
                })
            
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/weekly-story/comment/<int:comment_id>/delete', methods=['POST'])
    @login_required
    def delete_weekly_comment(comment_id):
        """Elimina un comentario de la historia de la semana (solo superusuario)"""
        if not current_user.is_superuser:
            return jsonify({'error': 'No tienes permiso'}), 403
        
        try:
            comment = WeeklyStoryComment.query.get_or_404(comment_id)
            db.session.delete(comment)
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/weekly-story/comment/<int:comment_id>/edit', methods=['POST'])
    @login_required
    def edit_weekly_comment(comment_id):
        """Edita un comentario de la historia de la semana (solo superusuario o propio)"""
        try:
            comment = WeeklyStoryComment.query.get_or_404(comment_id)
            
            # Solo superusuario o el usuario que creó el comentario
            if not current_user.is_superuser and comment.user_id != current_user.id:
                return jsonify({'error': 'No tienes permiso'}), 403
            
            content = request.form.get('content', '').strip()
            if not content:
                return jsonify({'error': 'El contenido no puede estar vacío'}), 400
            
            comment.content = content
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/comment/like', methods=['POST'])
    @login_required
    def toggle_comment_like():
        """Dar o quitar like a un comentario"""
        try:
            data = request.get_json()
            comment_id = data.get('comment_id')
            comment_type = data.get('comment_type')  # 'weekly' o 'story'
            
            if not comment_id or not comment_type:
                return jsonify({'error': 'Datos incompletos'}), 400
            
            # Solo superusuarios y nitalaosita pueden dar like
            if not (current_user.is_superuser or current_user.username == 'nitalaosita'):
                return jsonify({'error': 'No tienes permiso'}), 403
            
            # Obtener el comentario según el tipo
            if comment_type == 'weekly':
                comment = WeeklyStoryComment.query.get_or_404(comment_id)
            elif comment_type == 'story':
                comment = StoryComment.query.get_or_404(comment_id)
            elif comment_type == 'image':
                comment = ImageComment.query.get_or_404(comment_id)
            else:
                return jsonify({'error': 'Tipo de comentario inválido'}), 400
            
            # Verificar si ya existe el like
            existing_like = CommentLike.query.filter_by(
                user_id=current_user.id,
                comment_type=comment_type,
                comment_id=comment_id
            ).first()
            
            if existing_like:
                # Quitar like
                db.session.delete(existing_like)
                comment.likes_count = max(0, comment.likes_count - 1)
                liked = False
            else:
                # Agregar like
                new_like = CommentLike(
                    user_id=current_user.id,
                    comment_type=comment_type,
                    comment_id=comment_id
                )
                db.session.add(new_like)
                comment.likes_count = (comment.likes_count or 0) + 1
                liked = True
            
            db.session.commit()
            
            # Notificar actividad de nitalaosita
            if current_user.username == 'nitalaosita' and liked and _socketio:
                _socketio.emit('nita_activity', {
                    'type': 'like',
                    'icon': '❤️',
                    'text': 'Dio like a un comentario',
                    'link': '/weekly-story#comentarios',
                    'time': costa_rica_now_str()
                })
            
            return jsonify({
                'success': True,
                'liked': liked,
                'likes_count': comment.likes_count
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/comment/edit-likes', methods=['POST'])
    @login_required
    def edit_comment_likes():
        """Editar manualmente el contador de likes (solo superusuario)"""
        try:
            data = request.get_json()
            comment_id = data.get('comment_id')
            comment_type = data.get('comment_type')
            likes_count = data.get('likes_count')
            
            if not comment_id or not comment_type or likes_count is None:
                return jsonify({'error': 'Datos incompletos'}), 400
            
            # Solo superusuarios pueden editar likes manualmente
            if not current_user.is_superuser:
                return jsonify({'error': 'No tienes permiso'}), 403
            
            # Validar que sea un número válido
            try:
                likes_count = int(likes_count)
                if likes_count < 0:
                    return jsonify({'error': 'El número de likes no puede ser negativo'}), 400
            except ValueError:
                return jsonify({'error': 'Número inválido'}), 400
            
            # Obtener el comentario según el tipo
            if comment_type == 'weekly':
                comment = WeeklyStoryComment.query.get_or_404(comment_id)
            elif comment_type == 'story':
                comment = StoryComment.query.get_or_404(comment_id)
            elif comment_type == 'image':
                comment = ImageComment.query.get_or_404(comment_id)
            else:
                return jsonify({'error': 'Tipo de comentario inválido'}), 400
            
            comment.likes_count = likes_count
            db.session.commit()
            
            return jsonify({
                'success': True,
                'likes_count': comment.likes_count
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/weekly-story/<int:story_id>/clear-comments', methods=['POST'])
    @login_required
    def clear_weekly_comments(story_id):
        """Eliminar todos los comentarios de una historia (solo superusuario)"""
        try:
            if not current_user.is_superuser:
                return jsonify({'error': 'No tienes permiso'}), 403
            
            # Primero obtener los IDs de los comentarios
            comments = WeeklyStoryComment.query.filter_by(weekly_story_id=story_id).all()
            comment_ids = [c.id for c in comments]
            
            # Eliminar los likes asociados
            if comment_ids:
                CommentLike.query.filter(
                    CommentLike.comment_type == 'weekly',
                    CommentLike.comment_id.in_(comment_ids)
                ).delete(synchronize_session=False)
            
            # Eliminar todos los comentarios de la historia
            WeeklyStoryComment.query.filter_by(weekly_story_id=story_id).delete()
            
            db.session.commit()
            
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
