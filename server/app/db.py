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
CREATE TABLE IF NOT EXISTS files (
    name TEXT PRIMARY KEY,
    mime TEXT NOT NULL,
    data BLOB NOT NULL
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
        import_uploads(c)


MIME = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp'}


def sniff_image(data):
    """Return the file extension for JPEG, PNG or WebP data, or None."""
    if data[:3] == b'\xff\xd8\xff':
        return '.jpg'
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return '.png'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return '.webp'
    return None


def import_uploads(c):
    """Move photos saved as loose files by older versions into the database, so backups include them."""
    if not os.path.isdir(UPLOADS):
        return
    for name in os.listdir(UPLOADS):
        ext = os.path.splitext(name)[1].lower()
        path = os.path.join(UPLOADS, name)
        if ext in MIME and os.path.isfile(path):
            with open(path, 'rb') as f:
                c.execute('INSERT OR IGNORE INTO files (name, mime, data) VALUES (?, ?, ?)', (name, MIME[ext], f.read()))


def settings(c):
    return {r['key']: r['value'] for r in c.execute('SELECT key, value FROM settings')}
