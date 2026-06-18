"""SQLite persistence primitives (phase 9)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path("egodary.db")


def get_connection(path: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(cur: sqlite3.Cursor, table: str, column: str, col_type: str) -> None:
    cols = {row[1] for row in cur.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")


def init_db(path: Path | None = None) -> None:
    conn = get_connection(path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            positive TEXT NOT NULL,
            negative TEXT,
            model_id TEXT NOT NULL,
            result_url TEXT,
            settings_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS character_presets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS model_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS generation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            positive TEXT NOT NULL,
            negative TEXT,
            model_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS unknown_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT NOT NULL UNIQUE,
            source_prompt TEXT,
            hit_count INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'pending',
            suggested_category TEXT,
            suggested_subgroup TEXT,
            notes TEXT,
            first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
            last_seen TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_unknown_tags_status ON unknown_tags(status);
        CREATE INDEX IF NOT EXISTS idx_unknown_tags_hits ON unknown_tags(hit_count DESC);
        CREATE TABLE IF NOT EXISTS runtime_tag_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'import',
            item_json TEXT NOT NULL,
            original_phrase TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(category_id, item_id)
        );
        CREATE INDEX IF NOT EXISTS idx_runtime_tag_items_status ON runtime_tag_items(status);
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    _ensure_column(cur, "favorites", "result_url", "TEXT")
    _ensure_column(cur, "favorites", "settings_json", "TEXT")
    _ensure_column(cur, "unknown_tags", "suggested_subcategory", "TEXT")
    _ensure_column(cur, "unknown_tags", "resolution_status", "TEXT")
    conn.commit()
    conn.close()

