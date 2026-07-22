from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()
    
    # Verificar si el usuario ya existe
    existing = User.query.filter_by(email='nitalaosita@abc.com').first()
    if existing:
        print('Usuario nitalaosita@abc.com ya existe')
    else:
        # Crear el usuario
        user = User(
            email='nitalaosita@abc.com',
            username='nitalaosita',
            password_hash=generate_password_hash('nitalaosita'),
            is_superuser=True
        )
        db.session.add(user)
        db.session.commit()
        print('Usuario nitalaosita@abc.com creado exitosamente')
    
    # Listar todos los usuarios
    users = User.query.all()
    print(f'Total de usuarios: {len(users)}')
    for u in users:
        print(f'- {u.email} ({u.username}) - Superusuario: {u.is_superuser}')
