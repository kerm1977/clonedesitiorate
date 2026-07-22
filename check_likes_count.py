#!/usr/bin/env python3
"""
Script para verificar si la columna likes_count existe en las tablas de comentarios
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import WeeklyStoryComment, StoryComment

def check_likes_count():
    """Verificar si los comentarios tienen likes_count"""
    with app.app_context():
        # Verificar WeeklyStoryComment
        weekly_comments = WeeklyStoryComment.query.limit(5).all()
        print(f"Comentarios semanales: {len(weekly_comments)}")
        for comment in weekly_comments:
            try:
                print(f"  ID: {comment.id}, likes_count: {comment.likes_count}")
            except Exception as e:
                print(f"  ID: {comment.id}, ERROR: {e}")
        
        # Verificar StoryComment
        story_comments = StoryComment.query.limit(5).all()
        print(f"\nComentarios de historias: {len(story_comments)}")
        for comment in story_comments:
            try:
                print(f"  ID: {comment.id}, likes_count: {comment.likes_count}")
            except Exception as e:
                print(f"  ID: {comment.id}, ERROR: {e}")

if __name__ == '__main__':
    check_likes_count()
