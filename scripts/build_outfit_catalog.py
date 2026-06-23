"""Generate outfit_pack tag YAML files from the eGen 8.6 NSFW catalog."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from catalog_nsfw_data import (  # noqa: E402
    BOTTOM_GROUPS,
    BULKY_JACKET_IDS,
    CAPE_GROUPS,
    DRESS_GROUPS,
    DRESS_LAYER_SUBGROUPS,
    FOOTWEAR_GROUPS,
    GLOVES_GROUPS,
    JACKET_GROUPS,
    LAYERABLE_BOTTOM_SUBGROUPS,
    LEGWEAR_GROUPS,
    LONG_CAPE_IDS,
    OUTFIT_NONE_ITEMS,
    TOP_GROUPS,
)

ROOT = Path(__file__).resolve().parents[1] / "egodary" / "content" / "outfit_pack" / "tags"
RULES_PATH = Path(__file__).resolve().parents[1] / "egodary" / "content" / "outfit_pack" / "outfit_rules.yaml"

LEGWEAR_IDS = {
    "Garter Belt + Stockings": "garter_belt_stockings",
    "Fishnet with Garter": "fishnet_with_garter",
}


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


def tag_item(item_id: str, label: str, *, subgroup: str | None = None) -> dict:
    ill = label.lower()
    item: dict = {
        "id": item_id,
        "label": label,
        "tags": {
            "illustrious": ill,
            "anima": f"{ill}, styled outfit",
            "zimage_turbo": f"wearing {ill}",
        },
    }
    if subgroup:
        item["meta"] = {"subgroup": subgroup}
    return item


def none_item(field: str) -> dict:
    spec = OUTFIT_NONE_ITEMS[field]
    tags = spec["tags"]
    return {
        "id": "none",
        "label": spec["label"],
        "meta": {"subgroup": "none"},
        "tags": tags,
    }


def with_none_item(field: str, items: list[dict]) -> list[dict]:
    return [none_item(field), *items]


def items_from_groups(groups: dict[str, list[str]]) -> list[dict]:
    items: list[dict] = []
    for subgroup, labels in groups.items():
        for label in labels:
            items.append(tag_item(slug(label), label, subgroup=subgroup))
    return items


def subgroup_id_map(groups: dict[str, list[str]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for subgroup, labels in groups.items():
        for label in labels:
            mapping[slug(label)] = subgroup
    return mapping


def write_category(cat_id: str, title: str, items: list[dict]) -> None:
    path = ROOT / f"{cat_id.split('.')[-1]}.yaml"
    payload = {"id": cat_id, "title": title, "items": items}
    path.write_text(yaml.dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def write_outfit_rules() -> None:
    payload = {
        "bottom_subgroups": {
            subgroup: [slug(label) for label in labels]
            for subgroup, labels in BOTTOM_GROUPS.items()
        },
        "dress_subgroups": {
            subgroup: [slug(label) for label in labels]
            for subgroup, labels in DRESS_GROUPS.items()
        },
        "layerable_bottom_subgroups": list(LAYERABLE_BOTTOM_SUBGROUPS),
        "dress_layer_subgroups": list(DRESS_LAYER_SUBGROUPS),
        "legwear_ids": [
            LEGWEAR_IDS.get(label, slug(label))
            for labels in LEGWEAR_GROUPS.values()
            for label in labels
        ],
        "bulky_jackets": BULKY_JACKET_IDS,
        "long_capes": LONG_CAPE_IDS,
    }
    RULES_PATH.write_text(yaml.dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)

    write_category("outfit.dress", "Dress", with_none_item("dress", items_from_groups(DRESS_GROUPS)))
    write_category("outfit.top", "Top", with_none_item("top", items_from_groups(TOP_GROUPS)))
    write_category("outfit.jacket", "Jacket", with_none_item("jacket", items_from_groups(JACKET_GROUPS)))
    write_category("outfit.footwear", "Footwear", with_none_item("footwear", items_from_groups(FOOTWEAR_GROUPS)))
    write_category("outfit.gloves", "Gloves", with_none_item("gloves", items_from_groups(GLOVES_GROUPS)))
    write_category("outfit.cape", "Cape", with_none_item("cape", items_from_groups(CAPE_GROUPS)))

    bottom_items: list[dict] = []
    for subgroup, labels in BOTTOM_GROUPS.items():
        for label in labels:
            bottom_items.append(tag_item(slug(label), label, subgroup=subgroup))
    write_category("outfit.bottom", "Bottom", with_none_item("bottom", bottom_items))
    write_category(
        "outfit.legwear",
        "Legwear",
        with_none_item("legwear", items_from_groups(LEGWEAR_GROUPS)),
    )

    write_outfit_rules()
    print(f"Wrote outfit catalog to {ROOT}")


if __name__ == "__main__":
    main()
