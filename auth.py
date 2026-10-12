# auth.py
"""Auth helpers"""

import secrets
from urllib.parse import urlparse

import db
from flask import abort, flash, redirect, request, session, url_for
from werkzeug.security import check_password_hash


def authenticate_user(username: str, password: str) -> int | None:
    """Return the user ID if the credentials are valid, else None"""

    query = """
        SELECT id, password_hash
        FROM users
        WHERE username = ?
    """

    rows = db.query(query, [username])

    if len(rows) != 1:
        return None

    user_id = rows[0]["id"]
    password_hash = rows[0]["password_hash"]

    if not isinstance(user_id, int) or not isinstance(password_hash, str):
        return None

    if check_password_hash(password_hash, password):
        return user_id

    return None


def require_user_id() -> int:
    """Return the logged in user's ID or redirect to login page."""
    user_id = session.get("user_id")
    if isinstance(user_id, int):
        return user_id

    if request.method == "GET":
        next_page = request.full_path.removesuffix("?")
    else:
        next_page = _same_host_path(request.referrer)

    flash("Log in to continue")
    abort(redirect(url_for("login", next=next_page)))


def _same_host_path(url: str | None) -> str:
    """Path of a URL on host else '/'"""
    if not url:
        return "/"

    parsed = urlparse(url)
    if parsed.netloc != request.host:
        return "/"

    return f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path or "/"


def check_csrf() -> None:
    """Validate the CSRF token with the request"""
    form_token = request.form.get("csrf_token")
    session_token = session.get("csrf_token")

    if (
        form_token is None
        or session_token is None
        or not secrets.compare_digest(form_token, session_token)
    ):
        abort(403)


def safe_redirect_url(url: str) -> str:
    """Return a safe redirect URL, or '/' if unsafe."""
    parsed = urlparse(url)

    # reject outside urls
    if parsed.scheme or parsed.netloc:
        return "/"

    if not url.startswith("/"):
        return "/"

    return url
