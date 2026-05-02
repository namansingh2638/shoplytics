from functools import wraps
from flask import flash, redirect, url_for, session


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Access denied. Admins only.')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function