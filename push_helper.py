from pywebpush import webpush, WebPushException
import json
import os


def send_push_notification(subscription, data, vapid_private_key):
    """
    Enviar una notificación push a una suscripción específica
    
    Args:
        subscription: Objeto PushSubscription o dict con endpoint, p256dh, auth
        data: String o dict con el contenido de la notificación
        vapid_private_key: Clave privada VAPID
    """
    if isinstance(subscription, dict):
        subscription_info = {
            'endpoint': subscription['endpoint'],
            'keys': {
                'p256dh': subscription['p256dh'],
                'auth': subscription['auth']
            }
        }
    else:
        subscription_info = {
            'endpoint': subscription.endpoint,
            'keys': {
                'p256dh': subscription.p256dh,
                'auth': subscription.auth
            }
        }
    
    # Convertir data a string si es dict
    if isinstance(data, dict):
        data = json.dumps(data)
    
    try:
        webpush(
            subscription_info=subscription_info,
            data=data,
            vapid_private_key=vapid_private_key,
            vapid_claims={
                'sub': 'mailto:bolita@mummy.com'
            }
        )
        return True
    except WebPushException as e:
        print(f"Error enviando notificación: {e}")
        return False


def send_push_to_all(data, user_session=None):
    """
    Enviar notificación a todas las suscripciones o a una sesión específica
    
    Args:
        data: String o dict con el contenido de la notificación
        user_session: (opcional) ID de sesión específica
    """
    from models import PushSubscription
    
    # Cargar clave privada VAPID
    vapid_file = 'vapid_keys.json'
    if not os.path.exists(vapid_file):
        print("Claves VAPID no encontradas")
        return False
    
    with open(vapid_file, 'r') as f:
        keys = json.load(f)
        vapid_private_key = keys['private_key']
    
    # Obtener suscripciones
    if user_session:
        subscriptions = PushSubscription.query.filter_by(user_session=user_session).all()
    else:
        subscriptions = PushSubscription.query.all()
    
    # Enviar a cada suscripción
    success_count = 0
    for sub in subscriptions:
        if send_push_notification(sub, data, vapid_private_key):
            success_count += 1
    
    print(f"Notificaciones enviadas: {success_count}/{len(subscriptions)}")
    return success_count > 0


def send_push_to_session(user_session, data):
    """Enviar notificación a una sesión específica"""
    return send_push_to_all(data, user_session=user_session)
