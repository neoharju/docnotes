"""Helper functions for comments left on items"""

import sqlite3

import db


def create_comment(item_id: int, user_id: int, content: str) -> int | None:
    """Add a comment to an item. Returns the new comment's ID."""

    query = """
        INSERT INTO comments (item_id, user_id, content)
        VALUES (?, ?, ?)
    """
    db.execute(query, [item_id, user_id, content])
    return db.last_insert_id()


def get_comments(item_id: int) -> list[sqlite3.Row]:
    """Return all comments on an item, oldest first (reading order)"""

    query = """
        SELECT comments.id,
               comments.content, 
               datetime(comments.created_at, 'localtime') AS created_at,
               comments.user_id,
               users.username
        FROM comments
        JOIN users ON comments.user_id = users.id
        WHERE comments.item_id = ?
        ORDER BY comments.id ASC
    """
    return db.query(query, [item_id])


def get_comment(comment_id: int) -> sqlite3.Row | None:
    """Return a single comment's id/item_id/user_id by ID, else None"""

    query = "SELECT id, item_id, user_id FROM comments WHERE id = ?"
    rows = db.query(query, [comment_id])
    return rows[0] if rows else None


def delete_comment(comment_id: int) -> None:
    """Delete a comment by ID"""

    db.execute("DELETE FROM comments WHERE id = ?", [comment_id])
