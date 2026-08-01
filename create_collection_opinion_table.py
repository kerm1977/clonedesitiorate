from app import app, db
from models import CollectionOpinion

with app.app_context():
    db.create_all()
    print('Tabla collection_opinion creada (si no existía).')
