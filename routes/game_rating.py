from flask import request, jsonify, url_for
from models import db, Message, Favorite, ImageQuestion, ImageQuestionResponse, ScheduledUserMessage, Image, ImageComment, DeletedImage, CommentLike
from utils import get_session_id, log_activity
from datetime import datetime
from flask_login import current_user, login_required


def register_game_rating_routes(bp):
    

    @bp.route('/image/<int:image_id>/toggle-confetti', methods=['POST'])
    @login_required
    def toggle_image_confetti(image_id):
        if not current_user.is_superuser:
            return jsonify({'error': 'No tienes permiso'}), 403
        img = Image.query.get_or_404(image_id)
        img.has_confetti = not img.has_confetti
        db.session.commit()
        return jsonify({'success': True, 'has_confetti': img.has_confetti})


    @bp.route('/image/<int:image_id>/comments', methods=['GET'])
    def get_image_comments(image_id):
        comments = ImageComment.query.filter_by(image_id=image_id).order_by(ImageComment.created_at.desc()).all()
        uid = current_user.id if current_user.is_authenticated else None
        user_session = get_session_id()
        result = []
        for c in comments:
            is_liked = False
            if uid:
                is_liked = CommentLike.query.filter_by(user_id=uid, comment_type='image', comment_id=c.id).first() is not None
            elif user_session:
                is_liked = CommentLike.query.filter_by(user_session=user_session, comment_type='image', comment_id=c.id).first() is not None
            is_own = (uid and c.user_id == uid) or (not uid and c.user_session == user_session)
            result.append({
                'id': c.id,
                'username': c.username,
                'content': c.content,
                'likes_count': c.likes_count or 0,
                'is_liked': is_liked,
                'is_own': is_own,
                'user_id': c.user_id,
                'created_at': c.created_at.strftime('%d/%m/%Y %H:%M')
            })
        return jsonify(result)

    @bp.route('/image/<int:image_id>/comment', methods=['POST'])
    def add_image_comment(image_id):
        content = request.form.get('content', '').strip()
        if not content:
            return jsonify({'error': 'El comentario es obligatorio'}), 400
        
        # Determinar username
        if current_user.is_authenticated:
            if current_user.username == 'nitalaosita':
                username = current_user.username
            elif current_user.is_superuser:
                username = request.form.get('username', '').strip()
                if not username:
                    return jsonify({'error': 'El nombre es obligatorio'}), 400
            else:
                username = current_user.username if current_user.username else current_user.email
            user_id = current_user.id
            user_session = None
        else:
            username = request.form.get('username', '').strip()
            if not username:
                return jsonify({'error': 'El nombre es obligatorio'}), 400
            user_id = None
            user_session = get_session_id()
        
        comment = ImageComment(
            image_id=image_id,
            user_id=user_id,
            user_session=user_session,
            username=username,
            content=content
        )
        db.session.add(comment)
        db.session.commit()
        
        img = Image.query.get(image_id)
        if img:
            log_activity(username, 'comment', 'image_comment', img.filename,
                         object_url=url_for('game.view_image', image_id=image_id),
                         object_id=comment.id,
                         extra=content)
        
        return jsonify({
            'success': True,
            'comment': {
                'id': comment.id,
                'username': comment.username,
                'content': comment.content,
                'created_at': comment.created_at.strftime('%d/%m/%Y %H:%M')
            }
        })

    @bp.route('/image/comment/<int:comment_id>/edit', methods=['POST'])
    def edit_image_comment(comment_id):
        comment = ImageComment.query.get_or_404(comment_id)
        if current_user.is_authenticated:
            if not (current_user.is_superuser or comment.user_id == current_user.id):
                return jsonify({'error': 'No tienes permiso'}), 403
        else:
            if comment.user_session != get_session_id():
                return jsonify({'error': 'No tienes permiso'}), 403
        content = request.form.get('content', '').strip()
        if not content:
            return jsonify({'error': 'El contenido es obligatorio'}), 400
        comment.content = content
        db.session.commit()
        return jsonify({'success': True, 'content': comment.content})

    @bp.route('/image/comment/<int:comment_id>/delete', methods=['POST'])
    def delete_image_comment(comment_id):
        comment = ImageComment.query.get_or_404(comment_id)
        
        # Verificar permisos
        if current_user.is_authenticated:
            if current_user.is_superuser:
                # Superusuario puede eliminar cualquier comentario
                pass
            elif comment.user_id == current_user.id:
                # Usuario puede eliminar sus propios comentarios
                pass
            else:
                return jsonify({'error': 'No tienes permiso'}), 403
        else:
            # Usuario anónimo puede eliminar solo si coincide la sesión
            if comment.user_session != get_session_id():
                return jsonify({'error': 'No tienes permiso'}), 403
        
        db.session.delete(comment)
        db.session.commit()
        return jsonify({'success': True})

    @bp.route('/image/<int:image_id>/delete', methods=['POST'])
    def delete_image(image_id):
        if not current_user.is_authenticated or not (current_user.is_superuser or current_user.username == 'nitalaosita'):
            return jsonify({'error': 'No tienes permiso'}), 403
        
        image = Image.query.get_or_404(image_id)
        
        # Registrar la imagen eliminada
        deleted_image = DeletedImage(
            filename=image.filename,
            deleted_by_user_id=current_user.id
        )
        db.session.add(deleted_image)
        
        # Eliminar relaciones primero
        Favorite.query.filter_by(image_id=image_id).delete()
        ImageComment.query.filter_by(image_id=image_id).delete()
        ImageQuestion.query.filter_by(image_id=image_id).delete()
        Message.query.filter_by(trigger_image_id=image_id).delete()
        
        # Eliminar la imagen de la base de datos
        db.session.delete(image)
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Error al eliminar: {str(e)}'}), 500
        
        return jsonify({'success': True})
