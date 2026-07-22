from app import app, db
from models import AppConfig

with app.app_context():
    # Actualizar hostname de Tailscale a photobearrate
    cfg = AppConfig.query.filter_by(key='ts_hostname').first()
    if cfg:
        cfg.value = 'photobearrate'
        print('Hostname de Tailscale actualizado a photobearrate')
    else:
        db.session.add(AppConfig(key='ts_hostname', value='photobearrate'))
        print('Hostname de Tailscale creado como photobearrate')
    
    db.session.commit()
