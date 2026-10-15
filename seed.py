"""Fill database.db with a large amount of test data"""

import random
import sqlite3

from werkzeug.security import generate_password_hash

USER_COUNT = 1000
ITEM_COUNT = 10**5
COMMENT_COUNT = 10**6

KEYWORDS = [
    "physics",
    "mathematics",
    "computer science",
    "machine learning",
    "statistics",
    "chemistry",
    "biology",
    "medicine",
    "quantum computing",
    "ads/cft",
    "cryptography",
    "electronics",
    "simd",
]

# pdf starts with b"%PDF
PDF_DATA = b"%PDF-1.4\n%%EOF\n"


def main() -> None:
    """Add generated data to database.db"""

    con = sqlite3.connect("database.db")

    class_ids = [row[0] for row in con.execute("SELECT id FROM classes")]

    if not class_ids:
        raise SystemExit("No classes in the database: Do `sqlite3 database.db < schema.sql` first")

    # Generate data on top of existing data
    first_user = con.execute("SELECT coalesce(max(id), 0) + 1 FROM users").fetchone()[0]
    first_item = con.execute("SELECT coalesce(max(id), 0) + 1 FROM items").fetchone()[0]
    user_ids = range(first_user, first_user + USER_COUNT)
    item_ids = range(first_item, first_item + ITEM_COUNT)

    password_hash = generate_password_hash("my_test_password")

    # Add USER_COUNT=1000 users
    con.executemany(
        "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
        ((user_id, f"user{user_id}", password_hash) for user_id in user_ids),
    )
    # Add ITEM_COUNT=10**5 items
    con.executemany(
        """INSERT INTO items (id, user_id, title, filename, created_at)
           VALUES (?, ?, ?, ?, datetime('now', ?))""",
        (
            (
                item_id,
                random.choice(user_ids),
                f"PDF {item_id}",
                f"pdf{item_id}.pdf",
                f"-{item_ids[-1] - item_id} minutes",
            )
            for item_id in item_ids
        ),
    )

    con.executemany(
        "INSERT INTO item_files (item_id, pdf_data) VALUES (?, ?)",
        ((item_id, PDF_DATA) for item_id in item_ids),
    )

    con.executemany(
        "INSERT INTO item_keywords (item_id, keyword) VALUES (?, ?)",
        (
            (item_id, keyword)
            for item_id in item_ids
            for keyword in random.sample(KEYWORDS, random.randint(0, 3))
        ),
    )

    con.executemany(
        "INSERT INTO item_classes (item_id, class_id) VALUES (?, ?)",
        (
            (item_id, class_id)
            for item_id in item_ids
            for class_id in random.sample(class_ids, random.randint(1, 3))
        ),
    )

    # Add COMMENT_COUNT=10**6 comments
    con.executemany(
        "INSERT INTO comments (item_id, user_id, content) VALUES (?, ?, ?)",
        (
            (random.choice(item_ids), random.choice(user_ids), f"comment {i}")
            for i in range(1, COMMENT_COUNT + 1)
        ),
    )

    con.commit()
    con.close()


if __name__ == "__main__":
    main()
