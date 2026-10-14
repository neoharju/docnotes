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
     WHERE item_keywords.item_id = items.id) AS keywords,
    (SELECT count(*) FROM comments
     WHERE comments.item_id = items.id) AS comment_count
"""

SORT_ORDERS = {
    "recent": "items.id DESC",
    "comments": "comment_count DESC, items.id DESC",
}


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


def get_all_classes() -> dict[str, list[sqlite3.Row]]:
    """Selectable classes by title"""
    classes: dict[str, list[sqlite3.Row]] = {}
    for row in db.query("SELECT id, title, value FROM classes ORDER BY id"):
        classes.setdefault(row["title"], []).append(row)
    return classes


def get_item_classes(item_id: int) -> dict[str, list[str]]:
    """The item's classes by title: {"Type": ["Exam"], "Language": ["English"]}"""
    query = """
        SELECT classes.title, classes.value
        FROM item_classes
        JOIN classes ON classes.id = item_classes.class_id
        WHERE item_classes.item_id = ?
        ORDER BY classes.id
    """
    classes: dict[str, list[str]] = {}
    for row in db.query(query, [item_id]):
        classes.setdefault(row["title"], []).append(row["value"])
    return classes


def get_item_class_ids(item_id: int) -> list[int]:
    """IDs of the item's classes"""
    rows = db.query("SELECT class_id FROM item_classes WHERE item_id = ?", [item_id])
    return [row["class_id"] for row in rows]


def _insert_classes(con: sqlite3.Connection, item_id: int, class_ids: Sequence[int]) -> None:
    con.executemany(
        "INSERT INTO item_classes (item_id, class_id) VALUES (?, ?)",
        [(item_id, class_id) for class_id in class_ids],
    )


def create_item(
    user_id: int,
    title: str,
    filename: str,
    pdf_data: bytes,
    keywords: Sequence[str] = (),
    class_ids: Sequence[int] = (),
) -> int | None:
    """New items owned by user_id are linked with its keywords and classes"""

    query = """
        INSERT INTO items (user_id, title, filename)
        values (?, ?, ?)
    """
    with db.transaction() as con:
        item_id = con.execute(query, [user_id, title, filename]).lastrowid
        if item_id is not None:
            con.execute(
                "INSERT INTO item_files (item_id, pdf_data) VALUES (?, ?)", [item_id, pdf_data]
            )
            _insert_keywords(con, item_id, keywords)
            _insert_classes(con, item_id, class_ids)

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


def get_all_items(sort: str = "recent", limit: int = -1) -> list[sqlite3.Row]:
    """All items in SORT_ORDERS[sort] order"""

    query = f"""
        SELECT {_METADATA_COLS} 
        FROM items
        JOIN users ON items.user_id = users.id
        ORDER BY {SORT_ORDERS[sort]}
        LIMIT ?
    """
    return db.query(query, [limit])


def get_item_pdf(item_id: int) -> sqlite3.Row | None:
    """Returns filename and raw PDF bytes, else None"""

    query = """
        SELECT items.filename, item_files.pdf_data
        FROM items
        JOIN item_files ON item_files.item_id = items.id
        WHERE items.id = ?
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
    class_ids: Sequence[int] | None = None,
) -> None:
    """Edit an item's title, PDF, keywords or classes"""

    with db.transaction() as con:
        if filename is not None and pdf_data is not None:
            query = """
                UPDATE items
                SET title = ?, filename = ?
                WHERE id = ?
            """
            con.execute(query, [title, filename, item_id])
            con.execute("UPDATE item_files SET pdf_data = ? WHERE item_id = ?", [pdf_data, item_id])
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

        if class_ids is not None:
            con.execute("DELETE FROM item_classes WHERE item_id = ?", [item_id])
            _insert_classes(con, item_id, class_ids)


def _like_pattern(text: str) -> str:
    """Substring pattern: LIKE ... ESCAPE '\\' with % and _ in text"""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def search_items(text: str, sort: str = "recent") -> list[sqlite3.Row]:
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
        ORDER BY {SORT_ORDERS[sort]}
    """

    return db.query(query, [pattern, pattern, pattern, keyword_pattern])


def get_items_with_keyword(keyword: str, sort: str = "recent") -> list[sqlite3.Row]:
    """Items tagged with exactly this keyword, in SORT_ORDERS[sort] order"""

    query = f"""
        SELECT {_METADATA_COLS}
        FROM items
        JOIN users ON items.user_id = users.id
        WHERE items.id IN (SELECT item_id FROM item_keywords WHERE keyword = ?)
        ORDER BY {SORT_ORDERS[sort]}
    """

    return db.query(query, [keyword])


def delete_item(item_id: int) -> None:
    """Deletes item; its PDF, keywords and comments go by ON DELETE CASCADE"""

    query = """
        DELETE FROM items
        WHERE id = ?
    """
    db.execute(query, [item_id])
