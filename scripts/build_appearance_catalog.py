"""Generate appearance_pack tag YAML files."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from catalog_nsfw_data import ACCESSORIES_GROUPS, HAIR_COLOR_GROUPS, HAIR_GROUPS, MAKEUP_GROUPS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1] / "egodary" / "content" / "appearance_pack" / "tags"


def slug(label: str) -> str:
    return (
        label.lower()
        .replace("(", "")
        .replace(")", "")
        .replace("'", "")
        .replace("/", " ")
        .replace("+", " ")
        .replace("&", " ")
        .replace("-", " ")
        .replace("  ", " ")
        .strip()
        .replace(" ", "_")
    )


def hair_color_item(label: str, subgroup: str) -> dict:
    ill = label.lower()
    if "oil slick" in ill:
        ill = "oil slick hair, iridescent hair"
    elif not ill.endswith("hair"):
        ill = f"{ill} hair"
    return {
        "id": slug(label),
        "label": label,
        "meta": {"subgroup": subgroup},
        "tags": {
            "illustrious": ill,
            "anima": f"{ill}, detailed hairstyle",
            "zimage_turbo": f"with {ill}",
        },
    }


def hair_item(label: str, subgroup: str) -> dict:
    ill = label.lower()
    return {
        "id": slug(label),
        "label": label,
        "meta": {"subgroup": subgroup},
        "tags": {
            "illustrious": ill,
            "anima": f"{ill}, detailed hairstyle",
            "zimage_turbo": f"with {ill}",
        },
    }


def makeup_item(label: str, subgroup: str) -> dict:
    ill = label.lower()
    return {
        "id": slug(label),
        "label": label,
        "meta": {"subgroup": subgroup},
        "tags": {
            "illustrious": ill,
            "anima": f"{ill}, face makeup",
            "zimage_turbo": f"with {ill}",
        },
    }


def accessory_item(label: str, subgroup: str) -> dict:
    ill = label.lower()
    return {
        "id": slug(label),
        "label": label,
        "meta": {"subgroup": subgroup},
        "tags": {
            "illustrious": ill,
            "anima": f"{ill}, styled accessory",
            "zimage_turbo": f"wearing {ill}",
        },
    }


def items_from_groups(groups: dict[str, list[str]], factory) -> list[dict]:
    items: list[dict] = []
    for subgroup, labels in groups.items():
        for label in labels:
            items.append(factory(label, subgroup))
    return items


def write_category(cat_id: str, title: str, items: list[dict]) -> None:
    path = ROOT / f"{cat_id.split('.')[-1]}.yaml"
    payload = {"id": cat_id, "title": title, "items": items}
    path.write_text(yaml.dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    write_category("appearance.hair", "Hair", items_from_groups(HAIR_GROUPS, hair_item))
    write_category(
        "appearance.hair_color",
        "Hair Color",
        items_from_groups(HAIR_COLOR_GROUPS, hair_color_item),
    )
    write_category("appearance.makeup", "Makeup", items_from_groups(MAKEUP_GROUPS, makeup_item))
    write_category(
        "appearance.accessories",
        "Accessories",
        items_from_groups(ACCESSORIES_GROUPS, accessory_item),
    )
    print(f"Wrote appearance catalog to {ROOT}")


if __name__ == "__main__":
    main()
