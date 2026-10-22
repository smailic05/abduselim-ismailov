import os
import sqlite3
from contextlib import contextmanager

DATA_DIR = os.environ.get('DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
DB_PATH = os.path.join(DATA_DIR, 'site.db')
UPLOADS = os.path.join(DATA_DIR, 'uploads')

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS timeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year TEXT NOT NULL,
    text TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS works (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    subtitle TEXT NOT NULL DEFAULT '',
    section TEXT NOT NULL DEFAULT 'books',      -- books | prose | plays
    lang TEXT NOT NULL DEFAULT 'ru',            -- ru | lez | mix
    style TEXT NOT NULL DEFAULT 'prose',        -- prose | verse | play
    color INTEGER NOT NULL DEFAULT 0,
    visibility TEXT NOT NULL DEFAULT 'excerpt', -- full | excerpt | hidden
    excerpt_chars INTEGER NOT NULL DEFAULT 2200,
    body TEXT NOT NULL DEFAULT '',
    position INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

DEFAULT_SETTINGS = {
    'name': 'Абдуселим Исмаилов',
    'eyebrow': 'Народный писатель Дагестана',
    'tagline': '',
    'quote': '',
    'quote_source': '',
    'bio_lede': '',
    'bio': '',
    'stats': '',
    'footer': '',
    'photo': '',
}


def connect():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOADS, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


@contextmanager
def session():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init():
    with session() as c:
        c.executescript(SCHEMA)
        for k, v in DEFAULT_SETTINGS.items():
            c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (k, v))


def settings(c):
    return {r['key']: r['value'] for r in c.execute('SELECT key, value FROM settings')}
