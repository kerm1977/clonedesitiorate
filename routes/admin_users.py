from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from models import db, User, LoginAttempt

admin_users_bp = Blueprint('admin_users', __name__, url_prefix='/admin')


def _guard():
    return not current_user.is_authenticated or not current_user.is_superuser


@admin_users_bp.route('/password', methods=['POST'])
@login_required
def change_password():
    if _guard():
        return redirect(url_for('game.index'))
    new_pw = request.form.get('new_password', '').strip()
    if len(new_pw) >= 6:
        current_user.password_hash = generate_password_hash(new_pw)
        db.session.commit()
        flash('Contraseña actualizada', 'success')
    else:
        flash('La contraseña debe tener al menos 6 caracteres', 'error')
    return redirect(url_for('admin.admin'))


@admin_users_bp.route('/users/add', methods=['POST'])
@login_required
def add_user():
    if _guard():
        return redirect(url_for('game.index'))
    email = request.form.get('email', '').strip().lower()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    
    if not email or not password:
        flash('Email y contraseña son requeridos', 'error')
        return redirect(url_for('admin.admin') + '#tabUsuarios')
    
    if User.query.filter_by(email=email).first():
        flash('El email ya está registrado', 'error')
        return redirect(url_for('admin.admin') + '#tabUsuarios')
    
    if len(password) < 6:
        flash('La contraseña debe tener al menos 6 caracteres', 'error')
        return redirect(url_for('admin.admin') + '#tabUsuarios')
    
    db.session.add(User(
        email=email,
        username=username if username else None,
        password_hash=generate_password_hash(password),
        is_superuser=False
    ))
    db.session.commit()
    flash(f'Usuario {email} creado exitosamente', 'success')
    return redirect(url_for('admin.admin') + '#tabUsuarios')


@admin_users_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if _guard():
        return redirect(url_for('game.index'))
    user = User.query.get_or_404(user_id)
    if user.is_superuser:
        flash('No se pueden eliminar superusuarios', 'error')
        return redirect(url_for('admin.admin') + '#tabUsuarios')
    db.session.delete(user)
    db.session.commit()
    flash('Usuario eliminado', 'success')
    return redirect(url_for('admin.admin') + '#tabUsuarios')


@admin_users_bp.route('/blocked-ips/unblock/<int:attempt_id>', methods=['POST'])
@login_required
def unblock_ip(attempt_id):
    if _guard():
        return redirect(url_for('game.index'))
    attempt = LoginAttempt.query.get_or_404(attempt_id)
    db.session.delete(attempt)
    db.session.commit()
    flash(f'IP {attempt.ip_address} desbloqueada exitosamente', 'success')
    return redirect(url_for('admin.admin') + '#tabUsuarios')
