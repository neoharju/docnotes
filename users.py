# users.py
"""Helper functions for user management"""

import sqlite3

from werkzeug.security import generate_password_hash

import db


def create_user(username: str, password: str) -> int:
    """Create a new user account and return its ID"""
    password_hash = generate_password_hash(password)

    query = """
        INSERT INTO users (username, password_hash)
        VALUES (?, ?)
    """
    with db.transaction() as con:
        user_id = con.execute(query, [username, password_hash]).lastrowid

    if user_id is None:
        raise RuntimeError("INSERT INTO users returned no row id")
    return user_id


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


def get_stats(user_id: int) -> sqlite3.Row:
    """Stats for the user's profile page"""

    query = """
        SELECT
            (SELECT count(*) FROM items WHERE user_id = ?) AS pdfs,
            (SELECT count(*) FROM comments WHERE user_id = ?) AS comments_written,
            (SELECT count(*)
             FROM comments
             JOIN items ON items.id = comments.item_id
             WHERE items.user_id = ? AND comments.user_id != ?) AS comments_received
    """
    return db.query(query, [user_id] * 4)[0]
