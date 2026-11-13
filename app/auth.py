import secrets
from functools import wraps

from flask import abort, redirect, request, session, url_for

from .models import User, db


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def inject_template_context():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return {"csrf": session["csrf"], "me": current_user()}


def protect_post():
    if request.method == "POST":
        token = request.form.get("csrf_token", "")
        if not token or token != session.get("csrf"):
            abort(400)


def require_admin(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return redirect(url_for("main.login"))
        if user.role != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped
