from app import app
from models import db
from sqlalchemy import text

with app.app_context():
    # Agregar columna image_path a chat_message
    try:
        with db.engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE chat_message 
                ADD COLUMN image_path VARCHAR(255)
            """))
            conn.commit()
        print("Columna image_path agregada exitosamente")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print("La columna image_path ya existe")
        else:
            print(f"Error: {e}")
    
    # Para SQLite, necesitamos recrear la tabla para modificar content
    try:
        with db.engine.connect() as conn:
            # Crear tabla nueva con content nullable
            conn.execute(text("""
                CREATE TABLE chat_message_new (
                    id INTEGER NOT NULL PRIMARY KEY,
                    sender_id INTEGER,
                    sender_session VARCHAR(100),
                    sender_name VARCHAR(100) NOT NULL,
                    receiver_id INTEGER,
                    receiver_session VARCHAR(100),
                    receiver_name VARCHAR(100) NOT NULL,
                    chat_display_name VARCHAR(100),
                    content TEXT,
                    image_path VARCHAR(255),
                    created_at DATETIME,
                    is_read BOOLEAN,
                    FOREIGN KEY(sender_id) REFERENCES user (id),
                    FOREIGN KEY(receiver_id) REFERENCES user (id)
                )
            """))
            
            # Copiar datos
            conn.execute(text("""
                INSERT INTO chat_message_new 
                SELECT * FROM chat_message
            """))
            
            # Eliminar tabla vieja
            conn.execute(text("DROP TABLE chat_message"))
            
            # Renombrar tabla nueva
            conn.execute(text("ALTER TABLE chat_message_new RENAME TO chat_message"))
            
            conn.commit()
        print("Tabla recreada con content nullable")
    except Exception as e:
        print(f"Error al recrear tabla: {e}")
