"""Update database schema for new chat message fields"""
from app import app, db
from models import ChatMessage
from sqlalchemy import text

with app.app_context():
    # Check if columns exist
    inspector = db.inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('chat_message')]
    
    if 'edited' not in columns:
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE chat_message ADD COLUMN edited BOOLEAN DEFAULT FALSE'))
            conn.commit()
        print("Added 'edited' column")
    
    if 'edited_at' not in columns:
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE chat_message ADD COLUMN edited_at DATETIME'))
            conn.commit()
        print("Added 'edited_at' column")
    
    print("Database schema updated successfully")
