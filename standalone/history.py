"""
Historial de análisis guardado en SQLite.
"""

import json
from pathlib import Path
import sqlite3
from typing import Optional


DB_PATH = Path.home() / ".aca_history.db"


def init_db() -> None:
    """Crea la base SQLite y tabla analysis (id, created_at, bug, result_json)."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                bug TEXT NOT NULL,
                result_json TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def save_analysis(bug: str, result: dict) -> None:
    """Inserta un análisis en el historial."""
    from datetime import datetime
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO analysis (created_at, bug, result_json) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), bug, json.dumps(result, ensure_ascii=False))
        )
        conn.commit()
    finally:
        conn.close()


def get_recent(limit: int = 10) -> list[dict]:
    """Devuelve lista de dicts con id, created_at, bug, result_json."""
    conn = sqlite3.connect(DB_PATH)
    try:
        init_db()
        rows = conn.execute(
            "SELECT id, created_at, bug, result_json FROM analysis ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [
            {"id": r[0], "created_at": r[1], "bug": r[2], "result_json": r[3]}
            for r in rows
        ]
    finally:
        conn.close()


def clear_history() -> None:
    """Borra todos los registros del historial."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM analysis")
        conn.commit()
    finally:
        conn.close()
