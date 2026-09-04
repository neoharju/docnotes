# auth.py
"""Auth helpers"""

import secrets
from urllib.parse import urlparse

import db
from flask import abort, request, session
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
    """Require user to be authenticated"""
    user_id = session.get("user_id")

    if not isinstance(user_id, int):
        abort(403)

    return user_id


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
