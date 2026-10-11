"""Helper functions for data items management"""

import re
import sqlite3
import unicodedata
from collections.abc import Sequence

import db

MAX_KEYWORDS = 10
MAX_KEYWORD_LENGTH = 30
MAX_KEYWORDS_TEXT_LENGTH = 400

# keywords are separated by comma, so we split with this
_KEYWORD_RE = re.compile(r"\w[\w +#.\-]*")

_METADATA_COLS = """
    items.id, items.title, items.filename, datetime(items.created_at,
    'localtime') AS created_at, items.user_id, users.username,
    (SELECT group_concat(keyword, ',') FROM item_keywords
     WHERE item_keywords.item_id = items.id) AS keywords
"""


def normalize_keyword(text: str) -> str:
    """normalize keywords, so they can be grouped better;
    "Physics" and "PHysics" and "PHYSICS" become "physics"
    """
    return " ".join(unicodedata.normalize("NFKC", text).split()).lower()


def parse_keywords(text: str) -> list[str]:
    """keywords are commma-separated and normalized:

    'Physics, ML, physics' -> ['physics', 'ml']:
    """

    if len(text) > MAX_KEYWORDS_TEXT_LENGTH:
        raise ValueError("Keyword list is too long")

    keywords: list[str] = []
    for part in text.split(","):
        keyword = normalize_keyword(part)
        if not keyword or keyword in keywords:
            continue
        if len(keyword) > MAX_KEYWORD_LENGTH:
            raise ValueError(f"A keyword can be at most {MAX_KEYWORD_LENGTH} characters")
        if not _KEYWORD_RE.fullmatch(keyword):
            raise ValueError("Keywords can contain letters, numbers, spaces and + # . - _")
        if len(keywords) == MAX_KEYWORDS:
            raise ValueError(f"At most {MAX_KEYWORDS} keywords")
        keywords.append(keyword)

    return keywords


def keywords_text(keywords: str | None) -> str:
    """The "keywords" column ('ml,physics') as edit-form text ('ml, physics')"""
    return ", ".join(sorted(keywords.split(","))) if keywords else ""


def _insert_keywords(con: sqlite3.Connection, item_id: int, keywords: Sequence[str]) -> None:
    con.executemany(
        "INSERT INTO item_keywords (item_id, keyword) VALUES (?, ?)",
        [(item_id, keyword) for keyword in keywords],
    )


def create_item(
    user_id: int, title: str, filename: str, pdf_data: bytes, keywords: Sequence[str] = ()
) -> int | None:
    """New items owned by user_id are linked with its keywords"""

    query = """
        INSERT INTO items (user_id, title, filename, pdf_data)
        values (?, ?, ?, ?)
    """
    with db.transaction() as con:
        item_id = con.execute(query, [user_id, title, filename, pdf_data]).lastrowid
        if item_id is not None:
            _insert_keywords(con, item_id, keywords)

    return item_id


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
    item_id: int,
    title: str,
    filename: str | None = None,
    pdf_data: bytes | None = None,
    keywords: Sequence[str] | None = None,
) -> None:
    """Edit an item's title, PDF or keywords"""

    with db.transaction() as con:
        if filename is not None and pdf_data is not None:
            query = """
                UPDATE items
                SET title = ?, filename = ?, pdf_data = ?
                WHERE id = ?
            """
            con.execute(query, [title, filename, pdf_data, item_id])
        else:
            query = """
                UPDATE items
                SET title = ?
                WHERE id = ?
            """
            con.execute(query, [title, item_id])

        if keywords is not None:
            con.execute("DELETE FROM item_keywords WHERE item_id = ?", [item_id])
            _insert_keywords(con, item_id, keywords)


def _like_pattern(text: str) -> str:
    """Substring pattern: LIKE ... ESCAPE '\\' with % and _ in text"""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def search_items(text: str) -> list[sqlite3.Row]:
    """Search titles, filenames, uploaders and keywords by literal substring."""

    pattern = _like_pattern(text)
    keyword_pattern = _like_pattern(normalize_keyword(text))

    query = f"""
        SELECT {_METADATA_COLS}
        FROM items
        JOIN users ON items.user_id = users.id
        WHERE items.title LIKE ? ESCAPE '\\'
           OR items.filename LIKE ? ESCAPE '\\'
           OR users.username LIKE ? ESCAPE '\\'
           OR EXISTS (SELECT 1 FROM item_keywords
                      WHERE item_keywords.item_id = items.id
                        AND item_keywords.keyword LIKE ? ESCAPE '\\')
        ORDER BY items.id DESC
    """

    return db.query(query, [pattern, pattern, pattern, keyword_pattern])


def get_items_with_keyword(keyword: str) -> list[sqlite3.Row]:
    """Items tagged with exactly this keyword, most recent first"""

    query = f"""
        SELECT {_METADATA_COLS}
        FROM items
        JOIN users ON items.user_id = users.id
        WHERE items.id IN (SELECT item_id FROM item_keywords WHERE keyword = ?)
        ORDER BY items.id DESC
    """

    return db.query(query, [keyword])


def delete_item(item_id: int) -> None:
    """Deletes item and things related to it by foreign key"""

    query = """
        DELETE FROM items
        WHERE id = ?
    """
    db.execute(query, [item_id])
