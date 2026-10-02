from functools import wraps
from flask import session, flash, redirect, url_for, request
from database import get_db

def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.*, 
               sp.title as seeker_title, sp.resume_filename,
               ep.company_name, ep.logo_filename
        FROM users u
        LEFT JOIN seeker_profiles sp ON u.id = sp.user_id
        LEFT JOIN employer_profiles ep ON u.id = ep.user_id
        WHERE u.id = ? AND u.is_active = 1
    """, (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def login_required(roles=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login', next=request.url))
            
            user_role = session.get('role')
            if roles:
                allowed_roles = [roles] if isinstance(roles, str) else roles
                if user_role not in allowed_roles:
                    flash('You do not have permission to access this page.', 'danger')
                    return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
