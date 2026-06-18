"""Persistence layer (SQLite)."""

from egodary.persistence.db import init_db
from egodary.persistence.schema import list_favorites, save_favorite, save_generation_history

__all__ = ["init_db", "save_favorite", "list_favorites", "save_generation_history"]

