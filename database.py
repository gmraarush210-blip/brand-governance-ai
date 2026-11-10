"""
Persistence layer (SQLite). Owner: Aarush CU
Tables: submissions, revisions, findings, comments, decisions.
Original text is never overwritten: every edit is a new revision.
"""
import os
import sqlite3

DB_PATH = os.getenv("INKLOOM_DB", "inkloom.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL DEFAULT 'Untitled',
    content_type TEXT NOT NULL DEFAULT 'text',
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL REFERENCES submissions(id),
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    note TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL REFERENCES submissions(id),
    revision INTEGER NOT NULL DEFAULT 1,
    issue_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    excerpt TEXT DEFAULT '',
    explanation TEXT DEFAULT '',
    cited_source TEXT DEFAULT '',
    suggested_fix TEXT DEFAULT '',
    uncertainty TEXT DEFAULT '',
    state TEXT NOT NULL DEFAULT 'open',
    rejection_reason TEXT DEFAULT '',
    resolved_by TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL,
    finding_id INTEGER,
    author_role TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    decision TEXT NOT NULL,
    note TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
