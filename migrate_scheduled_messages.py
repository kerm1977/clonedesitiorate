from app import app, db
from models import ScheduledUserMessage

with app.app_context():
    # Guardar datos existentes
    existing_messages = ScheduledUserMessage.query.all()
    data = [(msg.user_id, msg.message, msg.scheduled_at, msg.shown, msg.created_at) for msg in existing_messages]
    
    # Eliminar la tabla
    ScheduledUserMessage.__table__.drop(db.engine)
    
    # Recrear la tabla con la nueva definición
    ScheduledUserMessage.__table__.create(db.engine)
    
    # Restaurar datos
    for user_id, message, scheduled_at, shown, created_at in data:
        db.session.add(ScheduledUserMessage(
            user_id=user_id,
            message=message,
            scheduled_at=scheduled_at,
            shown=shown,
            created_at=created_at
        ))
    
    db.session.commit()
    print(f'Tabla migrada exitosamente. {len(data)} mensajes restaurados.')
