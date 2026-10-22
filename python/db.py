import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).with_name("smart_office.db")

def connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def initialize():
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS face_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
            image_path TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL REFERENCES people(id),
            arrival_at TEXT NOT NULL,
            departure_at TEXT,
            duration_seconds INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_visits_open
        ON visits(person_id, departure_at);
        """)

def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")
