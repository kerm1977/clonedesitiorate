#!/usr/bin/env python3
"""Clear all login attempts from the database to unblock access."""
import os
import sys

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, LoginAttempt

app = create_app()

with app.app_context():
    # Delete all login attempts
    deleted = LoginAttempt.query.delete()
    db.session.commit()
    print(f"Deleted {deleted} login attempt records from the database.")
    print("Access has been unblocked.")
