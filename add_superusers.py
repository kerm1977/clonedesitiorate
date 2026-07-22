from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()
    
    # Crear o actualizar bolita@mummy.com
    bolita = User.query.filter_by(email='bolita@mummy.com').first()
    if not bolita:
        bolita = User(
            email='bolita@mummy.com',
            username='bolita',
            password_hash=generate_password_hash('vacavaca'),
            is_superuser=True
        )
        db.session.add(bolita)
        print('Usuario bolita@mummy.com creado')
    else:
        bolita.is_superuser = True
        bolita.password_hash = generate_password_hash('vacavaca')
        print('Usuario bolita@mummy.com actualizado')
    
    # Crear o actualizar doll@mummy.com
    doll = User.query.filter_by(email='doll@mummy.com').first()
    if not doll:
        doll = User(
            email='doll@mummy.com',
            username='doll',
            password_hash=generate_password_hash('vacavaca'),
            is_superuser=True
        )
        db.session.add(doll)
        print('Usuario doll@mummy.com creado')
    else:
        doll.is_superuser = True
        doll.password_hash = generate_password_hash('vacavaca')
        print('Usuario doll@mummy.com actualizado')
    
    # Asegurar que nitalaosita no sea superusuario
    nitalaosita = User.query.filter_by(email='nitalaosita@abc.com').first()
    if nitalaosita:
        nitalaosita.is_superuser = False
        print('Usuario nitalaosita@abc.com actualizado a regular')
    
    db.session.commit()
    
    # Listar todos los usuarios
    users = User.query.all()
    print(f'\nTotal de usuarios: {len(users)}')
    for u in users:
        print(f'- {u.email} ({u.username}) - Superusuario: {u.is_superuser}')
