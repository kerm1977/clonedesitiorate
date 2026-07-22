import os
import sys
from app import app, db
from models import Image, Rating, Favorite

def limpiar_imagenes_invalidas():
    """Elimina de la base de datos las imágenes que no existen en el disco"""
    with app.app_context():
        todas_imagenes = Image.query.all()
        total = len(todas_imagenes)
        invalidas = []
        
        print(f"Verificando {total} imagenes...")
        
        for img in todas_imagenes:
            if not os.path.exists(img.filepath):
                invalidas.append(img)
                print(f"[X] Imagen invalida: ID {img.id} - {img.filename}")
        
        if invalidas:
            print(f"\nSe encontraron {len(invalidas)} imagenes invalidas")
            print("Eliminando automaticamente...")
            
            # Primero eliminar ratings y favoritos asociados
            for img in invalidas:
                Rating.query.filter_by(image_id=img.id).delete()
                Favorite.query.filter_by(image_id=img.id).delete()
            
            # Luego eliminar las imagenes
            for img in invalidas:
                db.session.delete(img)
            
            db.session.commit()
            print(f"[OK] {len(invalidas)} imagenes eliminadas de la base de datos")
        else:
            print("[OK] Todas las imagenes son validas")

if __name__ == '__main__':
    limpiar_imagenes_invalidas()
