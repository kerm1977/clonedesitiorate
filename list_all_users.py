from app import app, db
from models import User

with app.app_context():
    users = User.query.all()
    print(f"Total usuarios: {len(users)}")
    for user in users:
        print(f"ID: {user.id}, Username: {user.username}, Email: {user.email}, Superuser: {user.is_superuser}")
