from app import app
from models import db, PushSubscription, User

with app.app_context():
    print("=== SUSCRIPCIONES PUSH ===")
    subs = PushSubscription.query.all()
    print(f"Total suscripciones: {len(subs)}")
    
    for sub in subs:
        print(f"\n- Username: {sub.username}")
        print(f"  Session: {sub.user_session}")
        print(f"  Endpoint: {sub.endpoint[:50]}...")
    
    print("\n=== USUARIOS ===")
    users = User.query.all()
    for user in users:
        user_subs = PushSubscription.query.filter_by(username=user.username).all()
        print(f"- {user.username}: {len(user_subs)} suscripciones")
