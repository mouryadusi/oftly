"""SQLite access and a simple versioned migration list (append new SQL to MIGRATIONS)."""
import sqlite3
from contextlib import contextmanager
from .config import db_path

MIGRATIONS = ["""
CREATE TABLE categories(id TEXT PRIMARY KEY, label TEXT NOT NULL, slot TEXT NOT NULL, sort INTEGER DEFAULT 0);
CREATE TABLE items(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT NOT NULL REFERENCES categories(id),
  subcategory TEXT DEFAULT '', image TEXT, primary_color TEXT DEFAULT '', secondary_colors TEXT DEFAULT '[]',
  pattern TEXT DEFAULT 'solid', brand TEXT DEFAULT '', product_url TEXT DEFAULT '', price REAL,
  description TEXT DEFAULT '', style TEXT DEFAULT '', occasions TEXT DEFAULT '[]', seasons TEXT DEFAULT '[]',
  formality INTEGER DEFAULT 3, favorite INTEGER DEFAULT 0, status TEXT DEFAULT 'available',
  notes TEXT DEFAULT '', is_demo INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX idx_items_cat ON items(category);
CREATE TABLE outfits(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT DEFAULT '', notes TEXT DEFAULT '',
  favorite INTEGER DEFAULT 0, score REAL, reason TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE outfit_items(outfit_id INTEGER NOT NULL REFERENCES outfits(id) ON DELETE CASCADE,
  item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE, PRIMARY KEY(outfit_id,item_id));
CREATE TABLE calendar(id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
  outfit_id INTEGER NOT NULL REFERENCES outfits(id) ON DELETE CASCADE, worn INTEGER DEFAULT 0, notes TEXT DEFAULT '');
CREATE INDEX idx_cal_date ON calendar(date);
CREATE TABLE feedback(id INTEGER PRIMARY KEY AUTOINCREMENT, signature TEXT NOT NULL, action TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE preferences(key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""]

# slot decides how the outfit generator uses a category (top, bottom, dress, shoes, bag, accessory)
DEFAULT_CATEGORIES = [
    ("shirts", "Shirts", "top"), ("tshirts", "T-shirts", "top"), ("tops_blouses", "Tops & Blouses", "top"),
    ("pants", "Pants & Trousers", "bottom"), ("jeans_shorts", "Jeans & Shorts", "bottom"),
    ("skirts", "Skirts", "bottom"), ("dresses", "Dresses & Frocks", "dress"),
    ("shoes", "Shoes & Footwear", "shoes"), ("bags", "Bags", "bag"), ("watches", "Watches", "accessory"),
    ("sunglasses", "Glasses & Sunglasses", "accessory"), ("jewelry", "Jewelry", "accessory"),
    ("belts", "Belts", "accessory"), ("other_accessories", "Other Accessories", "accessory"),
]

def connect():
    c = sqlite3.connect(db_path())
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

@contextmanager
def conn():
    c = connect()
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def init_db():
    with conn() as c:
        c.execute("CREATE TABLE IF NOT EXISTS schema_version(version INTEGER)")
        current = c.execute("SELECT MAX(version) v FROM schema_version").fetchone()["v"] or 0
        for n, sql in enumerate(MIGRATIONS, 1):
            if n > current:
                c.executescript(sql)
                c.execute("INSERT INTO schema_version VALUES(?)", (n,))
        if not c.execute("SELECT 1 FROM categories").fetchone():
            c.executemany("INSERT INTO categories(id,label,slot,sort) VALUES(?,?,?,?)",
                          [(i, l, s, n) for n, (i, l, s) in enumerate(DEFAULT_CATEGORIES)])
