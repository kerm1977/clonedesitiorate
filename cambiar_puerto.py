import re
import os

# Lista de puertos para probar
PUERTOS = [8080, 8000, 3000, 5000, 8888, 9000, 8081, 8082, 8083, 8084, 8085, 8086, 8087, 8088, 8089]

def cambiar_puerto_app(puerto):
    """Cambia el puerto en app.py"""
    app_file = 'app.py'
    
    if not os.path.exists(app_file):
        print(f"Error: No se encuentra {app_file}")
        return False
    
    with open(app_file, 'r', encoding='utf-8') as f:
        contenido = f.read()
    
    # Buscar y reemplazar el puerto en app.run
    patron = r"port=\d+"
    nuevo_contenido = re.sub(patron, f"port={puerto}", contenido)
    
    if nuevo_contenido == contenido:
        print(f"Error: No se encontró la línea 'port=' en {app_file}")
        return False
    
    with open(app_file, 'w', encoding='utf-8') as f:
        f.write(nuevo_contenido)
    
    print(f"✓ Puerto cambiado a {puerto} en app.py")
    return True

def main():
    print("=== Cambiador de Puerto para PhotoBearRate ===\n")
    print("Puertos disponibles:")
    for i, puerto in enumerate(PUERTOS, 1):
        print(f"{i}. Puerto {puerto}")
    
    try:
        seleccion = int(input("\nSelecciona el número del puerto que quieres usar: "))
        if seleccion < 1 or seleccion > len(PUERTOS):
            print("Selección inválida")
            return
        
        puerto = PUERTOS[seleccion - 1]
        
        if cambiar_puerto_app(puerto):
            print(f"\n✓ Listo! Ahora reinicia la app con el puerto {puerto}")
            print("   Ejecuta: python app.py")
            print(f"   O usa: iniciar_app.vbs")
        else:
            print("\n✗ Error al cambiar el puerto")
    
    except ValueError:
        print("Error: Debes ingresar un número")
    except KeyboardInterrupt:
        print("\nOperación cancelada")

if __name__ == '__main__':
    main()
