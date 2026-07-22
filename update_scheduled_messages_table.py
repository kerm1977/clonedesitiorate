from app import app, db
from models import ScheduledUserMessage
from sqlalchemy import text

with app.app_context():
    # Modificar la columna scheduled_at para permitir NULL
    db.session.execute(text('ALTER TABLE scheduled_user_message ALTER COLUMN scheduled_at DROP NOT NULL'))
    db.session.commit()
    print('Tabla ScheduledUserMessage actualizada para permitir mensajes inmediatos')
