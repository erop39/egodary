"""Generate outfit.clothing_condition tag YAML."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from catalog_clothing_conditions_data import CLOTHING_CONDITIONS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1] / "egodary" / "content" / "outfit_pack" / "tags"


def slug(text: str) -> str:
    return (
        text.lower()
        .replace("(", "")
        .replace(")", "")
        .replace("'", "")
        .replace("/", " ")
        .replace("+", " ")
        .replace("&", " ")
        .replace("-", " ")
        .replace(",", "")
        .replace("  ", " ")
        .strip()
        .replace(" ", "_")
    )


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    items: list[dict] = []
    used: set[str] = set()

    for field, groups in CLOTHING_CONDITIONS.items():
        for group, phrases in groups.items():
            for phrase in phrases:
                item_id = slug(phrase)
                if item_id in used:
                    item_id = f"{field}_{item_id}"
                used.add(item_id)
                items.append(
                    {
                        "id": item_id,
                        "label": phrase,
                        "meta": {"field": field, "group": group},
                        "tags": {
                            "illustrious": phrase,
                            "anima": f"{phrase}, clothing detail",
                            "zimage_turbo": f"wearing {phrase}",
                        },
                    }
                )

    payload = {
        "id": "outfit.clothing_condition",
        "title": "Clothing Condition",
        "items": items,
    }
    path = ROOT / "clothing_condition.yaml"
    path.write_text(yaml.dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"Wrote {len(items)} clothing conditions to {path}")


if __name__ == "__main__":
    main()
