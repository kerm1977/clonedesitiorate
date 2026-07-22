from app import app, db
from models import ScheduledUserMessage

with app.app_context():
    db.create_all()
    print('Tabla ScheduledUserMessage creada exitosamente')
