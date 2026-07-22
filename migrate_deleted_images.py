from app import app
from models import db, DeletedImage

with app.app_context():
    # Verificar si la tabla ya existe
    inspector = db.inspect(db.engine)
    if 'deleted_image' in inspector.get_table_names():
        print('La tabla deleted_image ya existe.')
    else:
        # Crear la tabla
        db.create_all()
        print('Tabla deleted_image creada exitosamente.')
