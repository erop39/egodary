"""Export runtime overlay items to plugins_user YAML."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import yaml

from egodary.core.runtime_registry import RuntimeRegistry
from egodary.config import DEFAULT_PLUGINS_USER_DIR


def export_overlay_to_plugins_user(
    registry: RuntimeRegistry,
    *,
    pack_dir: Path | None = None,
    pack_id: str = "imported_pack",
) -> list[Path]:
    target_root = pack_dir or (DEFAULT_PLUGINS_USER_DIR / pack_id)
    tags_dir = target_root / "tags"
    tags_dir.mkdir(parents=True, exist_ok=True)

    manifest = target_root / "manifest.toml"
    if not manifest.is_file():
        manifest.write_text(
            f'id = "{pack_id}"\nname = "Imported tags"\nversion = "0.1.0"\ntags_dir = "tags"\n',
            encoding="utf-8",
        )

    by_category: dict[str, list[dict]] = defaultdict(list)
    for category_id, item, meta in registry.list_overlay_items():
        row = item.model_dump()
        row["meta"] = {**row.get("meta", {}), "source": meta.source}
        by_category[category_id].append(row)

    written: list[Path] = []
    for category_id, items in by_category.items():
        safe_name = category_id.replace(".", "_")
        path = tags_dir / f"{safe_name}.yaml"
        payload = {
            "id": category_id,
            "title": category_id.replace(".", " / ").title(),
            "items": items,
        }
        path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
        written.append(path)
    return written
