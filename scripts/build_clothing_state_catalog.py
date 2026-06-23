"""Generate outfit.clothing_state tag YAML."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from catalog_clothing_state_data import (  # noqa: E402
    CLOTHING_STATE_DIMENSIONS,
    CLOTHING_STATE_ITEMS,
)

ROOT = Path(__file__).resolve().parents[1] / "egodary" / "content" / "outfit_pack" / "tags"


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    items: list[dict] = []
    used: set[str] = set()

    for dimension, entries in CLOTHING_STATE_ITEMS.items():
        group = CLOTHING_STATE_DIMENSIONS[dimension]
        for item_id, label, phrase in entries:
            if item_id in used:
                item_id = f"{dimension}_{item_id}"
            used.add(item_id)
            items.append(
                {
                    "id": item_id,
                    "label": label,
                    "meta": {"dimension": dimension, "group": group},
                    "tags": {
                        "illustrious": phrase,
                        "anima": f"{phrase}, clothing detail",
                        "zimage_turbo": f"wearing {phrase}",
                    },
                }
            )

    doc = {
        "id": "outfit.clothing_state",
        "title": "Clothing State",
        "items": items,
    }
    path = ROOT / "clothing_state.yaml"
    path.write_text(yaml.dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"Wrote {path} ({len(items)} items)")


if __name__ == "__main__":
    main()
