from app import app, db
from models import User

with app.app_context():
    # Actualizar chat_alias de doll y bolita para eliminar CamilaCR
    doll = User.query.filter_by(email='doll@mummy.com').first()
    if doll:
        print(f"doll - chat_alias actual: {doll.chat_alias}")
        doll.chat_alias = None
        print(f"doll - chat_alias nuevo: {doll.chat_alias}")
    
    bolita = User.query.filter_by(email='bolita@mummy.com').first()
    if bolita:
        print(f"bolita - chat_alias actual: {bolita.chat_alias}")
        bolita.chat_alias = None
        print(f"bolita - chat_alias nuevo: {bolita.chat_alias}")
    
    db.session.commit()
    print("Chat aliases actualizados correctamente")
