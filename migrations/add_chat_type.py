"""
Add chat_type field to ChatMessage table
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///photogame.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

def upgrade():
    with app.app_context():
        try:
            # Check if column already exists
            result = db.session.execute(text("PRAGMA table_info(chat_message)"))
            columns = [row[1] for row in result]
            if 'chat_type' in columns:
                print("Column chat_type already exists")
                return
            
            # Add chat_type column with default value 'private'
            db.session.execute(text('ALTER TABLE chat_message ADD COLUMN chat_type VARCHAR(20) DEFAULT "private"'))
            db.session.commit()
            print("Column chat_type added to chat_message table")
        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()

def downgrade():
    with app.app_context():
        try:
            db.session.execute(text('ALTER TABLE chat_message DROP COLUMN chat_type'))
            db.session.commit()
            print("Column chat_type dropped from chat_message table")
        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()

if __name__ == '__main__':
    upgrade()
