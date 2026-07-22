from app import app, db
from models import AppConfig

with app.app_context():
    # Actualizar puerto de Tailscale a 5001
    cfg = AppConfig.query.filter_by(key='ts_port').first()
    if cfg:
        cfg.value = '5001'
        print('Puerto de Tailscale actualizado a 5001')
    else:
        db.session.add(AppConfig(key='ts_port', value='5001'))
        print('Puerto de Tailscale creado como 5001')
    
    db.session.commit()
