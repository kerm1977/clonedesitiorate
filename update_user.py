from app import app, db, User

with app.app_context():
    user = User.query.filter_by(email='nitalaosita@abc.com').first()
    if user:
        user.is_superuser = False
        db.session.commit()
        print('Usuario nitalaosita@abc.com actualizado a usuario regular')
    else:
        print('Usuario no encontrado')
