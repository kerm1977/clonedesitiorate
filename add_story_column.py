import os
import sqlite3

def run_migration():
    db_paths = [
        os.path.join('instance', 'photogame.db'),
        'photogame.db',
        '../instance/photogame.db',
        '../photogame.db'
    ]

    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break

    if not db_path:
        os.makedirs('instance', exist_ok=True)
        db_path = os.path.join('instance', 'photogame.db')

    print(f"Connecting to database at: {os.path.abspath(db_path)}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE image ADD COLUMN story TEXT")
        conn.commit()
        print("Column 'story' added successfully to the 'image' table!")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column 'story' already exists in 'image' table.")
        else:
            print(f"OperationalError: {e}")
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    run_migration()
