# Lista de puertos comunes para servidores web
# Puedes usar estos puertos para encontrar el más rápido en tu red

PUERTOS = [
    8080,   # Puerto alternativo HTTP común
    8000,   # Puerto de desarrollo HTTP
    3000,   # Puerto común para Node.js
    5000,   # Puerto Flask por defecto
    8888,   # Puerto alternativo
    9000,   # Puerto alternativo
    8081,   # Puerto alternativo
    8082,   # Puerto alternativo
    8083,   # Puerto alternativo
    8084,   # Puerto alternativo
    8085,   # Puerto alternativo
    8086,   # Puerto alternativo
    8087,   # Puerto alternativo
    8088,   # Puerto alternativo
    8089,   # Puerto alternativo
]

print("Lista de puertos disponibles para probar velocidad:")
for i, puerto in enumerate(PUERTOS, 1):
    print(f"{i}. Puerto {puerto}")

print("\nPara cambiar el puerto en app.py, modifica la línea:")
print("app.run(debug=True, host='0.0.0.0', port=XXXX, ssl_context=ssl_context)")
print("Donde XXXX es el puerto que quieras usar.")
