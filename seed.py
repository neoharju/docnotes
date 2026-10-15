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

    password_hash = generate_password_hash("my_test_password")

    # Add USER_COUNT=1000 users
    con.executemany(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        ((f"user{i}", password_hash) for i in range(1, USER_COUNT + 1)),
    )
    # Add ITEM_COUNT=10**5 items
    con.executemany(
        """INSERT INTO items (user_id, title, filename, created_at)
           VALUES (?, ?, ?, datetime('now', ?))""",
        (
            (random.randint(1, USER_COUNT), f"PDF {i}", f"pdf{i}.pdf", f"-{ITEM_COUNT - i} minutes")
            for i in range(1, ITEM_COUNT + 1)
        ),
    )

    con.executemany(
        "INSERT INTO item_files (item_id, pdf_data) VALUES (?, ?)",
        ((i, PDF_DATA) for i in range(1, ITEM_COUNT + 1)),
    )

    con.executemany(
        "INSERT INTO item_keywords (item_id, keyword) VALUES (?, ?)",
        (
            (i, keyword)
            for i in range(1, ITEM_COUNT + 1)
            for keyword in random.sample(KEYWORDS, random.randint(0, 3))
        ),
    )

    con.executemany(
        "INSERT INTO item_classes (item_id, class_id) VALUES (?, ?)",
        (
            (i, class_id)
            for i in range(1, ITEM_COUNT + 1)
            for class_id in random.sample(class_ids, random.randint(1, 3))
        ),
    )

    # Add COMMENT_COUNT=10**6 comments
    con.executemany(
        "INSERT INTO comments (item_id, user_id, content) VALUES (?, ?, ?)",
        (
            (random.randint(1, ITEM_COUNT), random.randint(1, USER_COUNT), f"comment {i}")
            for i in range(1, COMMENT_COUNT + 1)
        ),
    )

    con.commit()
    con.close()


if __name__ == "__main__":
    main()
