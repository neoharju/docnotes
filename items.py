"""Helper functions for data items management"""

import sqlite3

import db

_METADATA_COLS = """
    items.id, items.title, items.filename, items.created_at, items.user_id,
    users.username
"""


def create_item(user_id: int, title: str, filename: str, pdf_data: bytes) -> int | None:
    """New item owned by user_id"""

    query = """
        INSERT INTO items (user_id, title, filename, pdf_data)
        values (?, ?, ?, ?)
    """
    db.execute(query, [user_id, title, filename, pdf_data])
    return db.last_insert_id()


def get_item(item_id: int) -> sqlite3.Row | None:
    """Search all users for item based on id, else None"""

    query = f"""
        SELECT {_METADATA_COLS} 
        FROM items
        JOIN users ON items.user_id = users.id
        WHERE items.id = ?
    """
    rows = db.query(query, [item_id])

    return rows[0] if rows else None


def get_all_items() -> list[sqlite3.Row]:
    """Get all items by users, else None"""

    query = f"""
        SELECT {_METADATA_COLS} 
        FROM items
        JOIN users ON items.user_id = users.id
        ORDER BY items.id DESC
    """
    return db.query(query)


def get_item_pdf(item_id: int) -> sqlite3.Row | None:
    """Returns filename and raw PDF bytes, else None"""

    query = """
        SELECT filename, pdf_data
        FROM items
        WHERE id = ?
    """

    rows = db.query(query, [item_id])
    return rows[0] if rows else None


def get_all_user_items(user_id: int) -> list[sqlite3.Row] | None:
    """Return user's items sorted by most recent, else None"""

    query = f"""
        SELECT {_METADATA_COLS}
        FROM items
        JOIN users ON items.user_id = users.id
        WHERE items.user_id = ?
        ORDER BY items.id DESC
    """
    rows = db.query(query, [user_id])
    return rows if rows else None


def edit_item(
    item_id: int, title: str, filename: str | None = None, pdf_data: bytes | None = None
) -> None:
    """Edit an item's title or replace the item"""

    if filename is not None and pdf_data is not None:
        query = """
            UPDATE items
            SET title = ?, filename = ?, pdf_data = ?
            WHERE id = ?
        """
        db.execute(query, [title, filename, pdf_data, item_id])
    else:
        query = """
            UPDATE items 
            SET title = ? 
            WHERE id = ?
        """
        db.execute(query, [title, item_id])


def search_items(keyword: str) -> list[sqlite3.Row]:
    """Search item metadata by literal substring."""

    escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    pattern = f"%{escaped}%"

    query = f"""
        SELECT {_METADATA_COLS}
        FROM items
        JOIN users ON items.user_id = users.id
        WHERE items.title LIKE ? ESCAPE '\\'
           OR items.filename LIKE ? ESCAPE '\\'
           OR users.username LIKE ? ESCAPE '\\'
        ORDER BY items.id DESC
    """

    return db.query(query, [pattern, pattern, pattern])


def delete_item(item_id: int) -> None:
    """Deletes item and things related to it by foreign key"""

    query = """
        DELETE FROM items
        WHERE id = ?
    """
    db.execute(query, [item_id])
