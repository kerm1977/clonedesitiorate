from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Story, WeeklyStory, StoryComment
from utils import log_activity
from datetime import datetime, timedelta

def register_admin_stories_routes(bp):
    
    @bp.route('/stories')
    @login_required
    def stories_admin():
        if not current_user.is_superuser:
            flash('No tienes permiso para ver esta página.', 'danger')
            return redirect(url_for('admin.admin'))
        
        stories = Story.query.order_by(Story.created_at.desc()).all()
        return render_template('admin_stories.html', stories=stories)
    
    @bp.route('/stories/<int:story_id>/delete', methods=['POST'])
    @login_required
    def delete_story_admin(story_id):
        if not current_user.is_superuser:
            return jsonify({'error': 'No tienes permiso'}), 403
        
        try:
            story = Story.query.get_or_404(story_id)
            db.session.delete(story)
            db.session.commit()
            flash('Historia eliminada exitosamente.', 'success')
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/stories/<int:story_id>/comment', methods=['POST'])
    @login_required
    def save_story_comment(story_id):
        if not current_user.is_superuser:
            return jsonify({'error': 'No tienes permiso'}), 403
        
        try:
            story = Story.query.get_or_404(story_id)
            comment = request.form.get('comment', '').strip()
            
            story.admin_comments = comment
            db.session.commit()
            
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/stories/<int:story_id>/add-comment', methods=['POST'])
    @login_required
    def add_story_comment(story_id):
        if not current_user.is_superuser:
            return jsonify({'error': 'No tienes permiso'}), 403
        
        try:
            story = Story.query.get_or_404(story_id)
            username = request.form.get('username', '').strip()
            content = request.form.get('content', '').strip()
            
            if not username or not content:
                return jsonify({'error': 'El nombre y el mensaje son obligatorios'}), 400
            
            comment = StoryComment(
                story_id=story_id,
                user_id=current_user.id if current_user.is_authenticated else None,
                user_session=None,
                username=username,
                content=content
            )
            db.session.add(comment)
            db.session.commit()
            
            log_activity(username, 'comment', 'story_comment', story.title or 'Historia',
                         object_url='/admin/stories',
                         object_id=comment.id,
                         extra=content)
            
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/stories/comment/<int:comment_id>/delete', methods=['POST'])
    @login_required
    def delete_story_comment(comment_id):
        """Elimina un comentario de historia (solo superusuario)"""
        if not current_user.is_superuser:
            return jsonify({'error': 'No tienes permiso'}), 403
        
        try:
            comment = StoryComment.query.get_or_404(comment_id)
            db.session.delete(comment)
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/stories/comment/<int:comment_id>/edit', methods=['POST'])
    @login_required
    def edit_story_comment(comment_id):
        """Edita un comentario de historia (solo superusuario o propio)"""
        try:
            comment = StoryComment.query.get_or_404(comment_id)
            
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
    
    @bp.route('/weekly-story')
    @login_required
    def weekly_story_admin():
        if not current_user.is_superuser:
            flash('No tienes permiso para ver esta página.', 'danger')
            return redirect(url_for('admin.admin'))
        
        today = datetime.utcnow()
        week_start = today - timedelta(days=today.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        current_story = WeeklyStory.query.filter_by(week_start=week_start).first()
        all_stories = WeeklyStory.query.order_by(WeeklyStory.week_start.desc()).all()
        
        return render_template('admin_weekly_story.html', 
                               current_story=current_story, 
                               all_stories=all_stories,
                               week_start=week_start)
    
    @bp.route('/weekly-story/save', methods=['POST'])
    @login_required
    def save_weekly_story():
        if not current_user.is_superuser:
            return jsonify({'error': 'No tienes permiso'}), 403
        
        try:
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            author = request.form.get('author', '').strip()
            week_start_str = request.form.get('week_start', '')
            
            print(f"DEBUG - title: {title}")
            print(f"DEBUG - content length: {len(content)}")
            print(f"DEBUG - author: {author}")
            print(f"DEBUG - week_start: {week_start_str}")
            
            if not title or not content or not author:
                flash('El título, el contenido y la autora son obligatorios.', 'danger')
                return redirect('/admin/weekly-story')
            
            week_start = datetime.strptime(week_start_str, '%Y-%m-%d')
            
            # Convertir enlaces photobearrate a HTML
            from utils import convert_photobearrate_links
            content = convert_photobearrate_links(content)
            
            story = WeeklyStory.query.filter_by(week_start=week_start).first()
            if story:
                story.title = title
                story.content = content
                story.author = author
                story.updated_at = datetime.utcnow()
            else:
                story = WeeklyStory(
                    title=title,
                    content=content,
                    author=author,
                    week_start=week_start,
                    active=True
                )
                db.session.add(story)
            
            db.session.commit()
            flash('Historia de la semana guardada exitosamente.', 'success')
            return redirect('/admin/weekly-story')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar: {str(e)}', 'danger')
            return redirect('/admin/weekly-story')
    
    @bp.route('/weekly-story/<int:story_id>/delete', methods=['POST'])
    @login_required
    def delete_weekly_story(story_id):
        if not current_user.is_superuser:
            return jsonify({'error': 'No tienes permiso'}), 403
        
        try:
            story = WeeklyStory.query.get_or_404(story_id)
            db.session.delete(story)
            db.session.commit()
            flash('Historia de la semana eliminada exitosamente.', 'success')
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/weekly-story/<int:story_id>/get', methods=['GET'])
    @login_required
    def get_weekly_story(story_id):
        """Obtener los datos de una historia para editar"""
        if not current_user.is_superuser:
            return jsonify({'error': 'No tienes permiso'}), 403
        
        try:
            story = WeeklyStory.query.get_or_404(story_id)
            return jsonify({
                'story': {
                    'id': story.id,
                    'title': story.title,
                    'content': story.content,
                    'author': story.author,
                    'week_start': story.week_start.strftime('%Y-%m-%d'),
                    'active': story.active
                }
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @bp.route('/weekly-story/<int:story_id>/activate', methods=['POST'])
    @login_required
    def activate_weekly_story(story_id):
        if not current_user.is_superuser:
            return jsonify({'error': 'No tienes permiso'}), 403
        
        try:
            # Desactivar todas las historias
            db.session.query(WeeklyStory).update({'active': False})
            
            # Activar la seleccionada
            story = WeeklyStory.query.get_or_404(story_id)
            story.active = True
            db.session.commit()
            
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
