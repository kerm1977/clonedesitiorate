import json
import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# Generar nuevas claves VAPID
private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())

# Obtener clave privada en formato PEM (para pywebpush)
private_key_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
).decode('utf-8')

# Obtener clave pública en formato DER (para base64)
public_key = private_key.public_key()
public_key_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)

# Convertir a base64 URL-safe
public_key_base64 = base64.urlsafe_b64encode(public_key_bytes).decode('utf-8').rstrip('=')

# Guardar en archivo
vapid_keys = {
    'private_key': private_key_pem,  # PEM para pywebpush
    'public_key': public_key_base64  # Base64 para frontend
}

with open('vapid_keys.json', 'w') as f:
    json.dump(vapid_keys, f, indent=2)

print("Claves VAPID regeneradas")
print(f"Public Key (base64): {public_key_base64}")
print(f"Private Key (PEM):\n{private_key_pem}")
