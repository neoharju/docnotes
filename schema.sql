CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

CREATE TABLE items (
	id INTEGER PRIMARY KEY,
	user_id INTEGER NOT NULL,
	title TEXT NOT NULL,
	filename TEXT NOT NULL,
	created_at TEXT NOT NULL DEFAULT (datetime('now')),
	FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE INDEX idx_items_user_id ON items (user_id);

CREATE TABLE item_files (
	item_id INTEGER PRIMARY KEY,
	pdf_data BLOB NOT NULL,
	FOREIGN KEY (item_id) REFERENCES items (id) ON DELETE CASCADE
);

CREATE TABLE comments (
    id INTEGER PRIMARY KEY,
    item_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (item_id) REFERENCES items (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE INDEX idx_comments_item_id ON comments (item_id);
CREATE INDEX idx_comments_user_id ON comments (user_id);

CREATE TABLE item_keywords (
    item_id INTEGER NOT NULL,
    keyword TEXT NOT NULL,
    PRIMARY KEY (item_id, keyword),
    FOREIGN KEY (item_id) REFERENCES items (id) ON DELETE CASCADE
) WITHOUT ROWID;

CREATE INDEX idx_item_keywords_keyword ON item_keywords (keyword);

CREATE TABLE classes (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    value TEXT NOT NULL,
    UNIQUE (title, value)
);

INSERT OR IGNORE INTO classes (title, value) VALUES
    ('Type', 'Lecture notes'),
    ('Type', 'Exercises'),
    ('Type', 'Exam'),
    ('Type', 'Article'),
    ('Type', 'Thesis'),
    ('Type', 'Book');

CREATE TABLE item_classes (
    item_id INTEGER NOT NULL,
    class_id INTEGER NOT NULL,
    PRIMARY KEY (item_id, class_id),
    FOREIGN KEY (item_id) REFERENCES items (id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes (id)
) WITHOUT ROWID;
