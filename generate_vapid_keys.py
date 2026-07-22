from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64
import json

# Generar clave privada EC (P-256)
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()

# Convertir a formato base64 URL-safe
private_key_bytes = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

public_key_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)

# Convertir a base64 URL-safe
private_key_base64 = base64.urlsafe_b64encode(private_key_bytes).decode('utf-8').rstrip('=')
public_key_base64 = base64.urlsafe_b64encode(public_key_bytes).decode('utf-8').rstrip('=')

vapid_keys = {
    'public_key': public_key_base64,
    'private_key': private_key_base64
}

with open('vapid_keys.json', 'w') as f:
    json.dump(vapid_keys, f, indent=2)

print("Claves VAPID generadas:")
print(f"Public Key: {public_key_base64}")
print(f"Private Key: {private_key_base64}")
print("Guardadas en vapid_keys.json")
