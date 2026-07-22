from app import app, db
from models import User

with app.app_context():
    # Buscar usuario con username CamilaCR o que contenga camila
    users_to_delete = User.query.filter(
        db.or_(
            User.username.ilike('%camila%'),
            User.email.ilike('%camila%')
        )
    ).all()
    
    print(f"Usuarios encontrados con 'camila': {len(users_to_delete)}")
    for user in users_to_delete:
        print(f"  - ID: {user.id}, Username: {user.username}, Email: {user.email}")
    
    if users_to_delete:
        confirm = input("¿Eliminar estos usuarios? (s/n): ")
        if confirm.lower() == 's':
            for user in users_to_delete:
                # Eliminar mensajes de chat del usuario
                from models import ChatMessage
                ChatMessage.query.filter_by(sender_id=user.id).delete()
                ChatMessage.query.filter_by(sender_name=user.username).delete()
                ChatMessage.query.filter_by(receiver_name=user.username).delete()
                
                db.session.delete(user)
                print(f"Eliminado: {user.username}")
            db.session.commit()
            print("Usuarios eliminados correctamente")
        else:
            print("Cancelado")
    else:
        print("No se encontraron usuarios con 'camila'")
