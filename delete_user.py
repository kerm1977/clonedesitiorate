#!/usr/bin/env python3
"""Delete user with ID 18003 from the database."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, User, Rating, ChatMessage, Favorite

app = create_app()

with app.app_context():
    user = User.query.get(18003)
    if user:
        # Delete related records
        Rating.query.filter_by(user_session=str(user.id)).delete()
        ChatMessage.query.filter_by(sender=user.username).delete()
        ChatMessage.query.filter_by(receiver_name=user.username).delete()
        Favorite.query.filter_by(user_session=str(user.id)).delete()
        
        # Delete the user
        db.session.delete(user)
        db.session.commit()
        print(f"User {user.username} (ID: {user.id}) deleted successfully.")
    else:
        print("User with ID 18003 not found.")
