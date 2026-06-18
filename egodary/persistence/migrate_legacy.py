"""Migrate eGen legacy exportSettings JSON to sqlite records."""

from __future__ import annotations

import json
from pathlib import Path

from egodary.persistence.db import init_db
from egodary.persistence.schema import save_favorite


def migrate_legacy_export(path: Path) -> dict:
    init_db()
    data = json.loads(path.read_text(encoding="utf-8"))
    imported = 0
    skipped = 0
    favorites = data.get("favorites", [])
    for fav in favorites:
        positive = fav.get("prompt") or fav.get("positive") or ""
        if not positive:
            skipped += 1
            continue
        save_favorite(
            name=fav.get("name", f"legacy_{imported+1}"),
            positive=positive,
            negative=fav.get("negative"),
            model_id=fav.get("model", "illustrious"),
        )
        imported += 1
    return {"imported": imported, "skipped": skipped, "source": str(path)}

