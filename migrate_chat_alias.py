from app import app
from models import db, User
from sqlalchemy import text

with app.app_context():
    # Agregar columna chat_alias a user
    try:
        with db.engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE user 
                ADD COLUMN chat_alias VARCHAR(100)
            """))
            conn.commit()
        print("Columna chat_alias agregada exitosamente")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print("La columna chat_alias ya existe")
        else:
            print(f"Error: {e}")
    
    # Actualizar alias de usuarios específicos
    try:
        # doll@mummy.com -> Danita
        doll = User.query.filter_by(email='doll@mummy.com').first()
        if doll:
            doll.chat_alias = 'Danita'
            print(f"Alias 'Danita' asignado a {doll.email}")
        
        # bolita@mummy.com -> pedomom67
        bolita = User.query.filter_by(email='bolita@mummy.com').first()
        if bolita:
            bolita.chat_alias = 'pedomom67'
            print(f"Alias 'pedomom67' asignado a {bolita.email}")
        
        db.session.commit()
        print("Alias actualizados exitosamente")
    except Exception as e:
        print(f"Error al actualizar alias: {e}")
