"""Toda interacción con SQLite pasa por acá."""

import sqlite3
from pathlib import Path
from app.config import DB_PATH


def get_connection() -> sqlite3.Connection:
    db_file = Path(DB_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def execute_script(script_path: str) -> None:
    with get_connection() as conn:
        with open(script_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()


def fetch_all(query: str, params: tuple = ()) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def fetch_one(query: str, params: tuple = ()) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None


def execute(query: str, params: tuple = ()) -> int:
    with get_connection() as conn:
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.lastrowid


def execute_many(query: str, params_list: list[tuple]) -> None:
    with get_connection() as conn:
        conn.executemany(query, params_list)
        conn.commit()
