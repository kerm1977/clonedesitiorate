from app import app, db
from sqlalchemy import text

with app.app_context():
    # Agregar columnas nuevas
    db.session.execute(text('ALTER TABLE scheduled_user_message ADD COLUMN response TEXT'))
    db.session.execute(text('ALTER TABLE scheduled_user_message ADD COLUMN responded_at DATETIME'))
    db.session.commit()
    print('Columnas response y responded_at agregadas exitosamente')
