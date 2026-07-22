from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from models import db, User, Notification, LoginAttempt

auth_bp = Blueprint('auth', __name__)

_auth_socketio = None

def set_auth_socketio(sio):
    global _auth_socketio
    _auth_socketio = sio

MAX_ATTEMPTS = 10


def _get_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('game.index'))
    
    ip = _get_ip()
    attempt = LoginAttempt.query.filter_by(ip_address=ip).first()
    
    # Si la IP está bloqueada, mostrar página bloqueada
    if attempt and attempt.blocked:
        return render_template('login_blocked.html')
    
    if request.method == 'POST':
        u = User.query.filter_by(email=request.form['email'].strip().lower()).first()
        if u and check_password_hash(u.password_hash, request.form['password']):
            # Login exitoso: limpiar intentos fallidos
            if attempt:
                db.session.delete(attempt)
            login_user(u)
            if u.username == 'nitalaosita' and _auth_socketio:
                _auth_socketio.emit('nita_connected', {}, namespace='/')
            username = u.username if u.username else u.email
            db.session.add(Notification(
                message=f'Usuario {username} se ha conectado',
                notification_type='user_login'
            ))
            db.session.commit()
            next_page = request.args.get('next')
            return redirect(next_page or url_for('game.index'))
        
        # Login fallido: registrar intento
        if not attempt:
            attempt = LoginAttempt(ip_address=ip, failed_count=1)
            db.session.add(attempt)
        else:
            attempt.failed_count += 1
        
        if attempt.failed_count >= MAX_ATTEMPTS:
            attempt.blocked = True
            db.session.commit()
            return render_template('login_blocked.html')
        
        db.session.commit()
        remaining = MAX_ATTEMPTS - attempt.failed_count
        flash(f'Correo o contraseña incorrectos. Te queda {remaining} intento(s).', 'error')
    
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('game.index'))
