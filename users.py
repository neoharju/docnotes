# users.py
"""Helper functions for user management"""

import sqlite3

import db
from werkzeug.security import generate_password_hash


def create_user(username: str, password: str) -> None:
    """Create a new user account"""
    password_hash = generate_password_hash(password)

    query = """
        INSERT INTO users (username, password_hash)
        VALUES (?, ?)
    """
    db.execute(query, [username, password_hash])


def get_user(user_id: int) -> sqlite3.Row | None:
    """Return user's public info by ID, else None"""

    query = """
        SELECT id, username
        FROM users
        WHERE id = ?
    """

    rows = db.query(query, [user_id])

    if not rows:
        return None

    return rows[0]


def get_messages(user_id: int) -> None:
    """Get user messages"""


def get_papers(user_id: int) -> None:
    """Get user submitted papers"""


def set_image(user_id: int, image: bytes) -> None:
    """Set user image"""


def get_image(user_id: int) -> bytes | None:
    """Get user image"""
