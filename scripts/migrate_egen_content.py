"""One-shot migrator: eGen 8.6.html -> egodary content YAML packs."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

EGEN_HTML = Path(__file__).resolve().parents[2] / "eGendary" / "eGen 8.6.html"
CONTENT = Path(__file__).resolve().parents[1] / "egodary" / "content"


def _label(item_id: str) -> str:
    return item_id.replace("_", " ").title()


def _zimage(phrase: str) -> str:
    return f"in a scene with {phrase}"


def _write_category(path: Path, category_id: str, title: str, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"id": category_id, "title": title, "items": items}
    path.write_text(yaml.dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _item_simple(item_id: str, illustrious: str, anima: str | None = None) -> dict:
    anima_text = anima or illustrious
    return {
        "id": item_id,
        "label": _label(item_id),
        "tags": {
            "illustrious": illustrious,
            "anima": anima_text,
            "zimage_turbo": _zimage(anima_text if anima else illustrious),
        },
    }


def migrate_environment_library(text: str) -> tuple[list[dict], dict[str, list[str]]]:
    match = re.search(r"const ENVIRONMENT_LIBRARY = \{(.*?)\n\};", text, re.S)
    if not match:
        raise RuntimeError("ENVIRONMENT_LIBRARY not found")
    body = match.group(1)
    items: list[dict] = []
    groups: dict[str, list[str]] = {}
    for group_match in re.finditer(r"(\w+):\s*\[(.*?)\]\s*,?", body, re.S):
        group = group_match.group(1)
        group_body = group_match.group(2)
        groups[group] = []
        for loc in re.finditer(
            r'\{\s*id:\s*"([^"]+)",\s*illustrious:\s*"([^"]+)",\s*anima:\s*"([^"]+)"\s*\}',
            group_body,
        ):
            item_id, ill, anima = loc.groups()
            groups[group].append(item_id)
            items.append(
                {
                    **_item_simple(item_id, ill, anima),
                    "meta": {"environment_group": group},
                }
            )
    return items, groups


def migrate_outfit_map(text: str, key: str, category_id: str, title: str) -> list[dict]:
    pattern = rf"{key}:\s*\{{(.*?)\n\s*\}},"
    match = re.search(pattern, text, re.S)
    if not match:
        raise RuntimeError(f"OUTFIT_TAGS.{key} not found")
    block = match.group(1)
    items = []
    for item_id, tag in re.findall(r"(\w+):\s*\"([^\"]+)\"", block):
        items.append(_item_simple(item_id, tag))
    return items


def migrate_fetish_catalog(text: str) -> tuple[list[tuple[str, str, list[dict]]], list[list[str]]]:
    match = re.search(r"const FETISH_CATALOG = \[(.*?)\n\];", text, re.S)
    if not match:
        raise RuntimeError("FETISH_CATALOG not found")
    body = match.group(1)
    categories: list[tuple[str, str, list[dict]]] = []
    for cat in re.finditer(
        r"\{\s*id:\s*'([^']+)',\s*title:\s*'([^']*)'.*?items:\s*\[(.*?)\]\s*\}",
        body,
        re.S,
    ):
        cat_id, title, items_block = cat.groups()
        items = []
        for item in re.finditer(
            r"\{\s*id:\s*'([^']+)',\s*label:\s*'([^']*)'(?:,\s*minLevel:\s*(\d+))?,\s*tag:\s*FETISH_TAG\('([^']*)',\s*'([^']*)'\)\s*\}",
            items_block,
            re.S,
        ):
            item_id, label, min_level, ill, anima = item.groups()
            entry = _item_simple(item_id, ill, anima)
            entry["label"] = label
            if min_level:
                entry["min_level"] = int(min_level)
            items.append(entry)
        categories.append((cat_id, title, items))

    conflict_match = re.search(r"const FETISH_CONFLICT_GROUPS = \[(.*?)\];", text, re.S)
    groups: list[list[str]] = []
    if conflict_match:
        for group in re.findall(r"\[([^\]]+)\]", conflict_match.group(1)):
            ids = [x.strip().strip("'\"") for x in group.split(",") if x.strip()]
            groups.append(ids)
    return categories, groups


def migrate_external_skip(text: str) -> dict[str, list[dict]]:
    match = re.search(r"const FETISH_EXTERNAL_SKIP = \{(.*?)\};", text, re.S)
    if not match:
        return {}
    rules: dict[str, list[dict]] = {}
    for item_id, body in re.findall(r"(\w+):\s*\(\)\s*=>\s*([^,}]+)", match.group(1)):
        checks: list[dict] = []
        for field, value in re.findall(r"selected(\w+)\s*===\s*'([^']+)'", body):
            checks.append({"field": _field_name(field), "equals": value.lower()})
        for field in re.findall(r"selected(\w+)\.includes\('([^']+)'\)", body):
            checks.append({"field": _field_name(field[0]), "includes": field[1]})
        for field in re.findall(r"!!selected(\w+)\s*&&\s*selected\1\s*!==\s*'([^']+)'", body):
            checks.append({"field": _field_name(field[0]), "not_equals": field[1]})
        if "hasLegDetailFocus()" in body:
            checks.append({"field": "leg_detail_focus", "equals": True})
        rules[item_id] = checks
    return rules


def _field_name(camel: str) -> str:
    mapping = {
        "Personality": "personality",
        "Expression": "expression",
        "MoodPreset": "mood_preset",
        "AtmosphereLayer": "atmosphere",
        "Occupation": "occupation",
        "Archetype": "archetype",
        "Waist": "waist",
        "NeckAccessories": "neck_accessories",
        "Jacket": "outfit.jacket",
        "Bottom": "outfit.bottom",
    }
    return mapping.get(camel, camel.lower())


def main() -> None:
    text = EGEN_HTML.read_text(encoding="utf-8")

    # scene locations
    loc_items, loc_groups = migrate_environment_library(text)
    _write_category(
        CONTENT / "scene_location_pack" / "tags" / "location.yaml",
        "scene.location",
        "Location",
        loc_items,
    )
    (CONTENT / "scene_location_pack" / "location_groups.yaml").write_text(
        yaml.dump({"groups": loc_groups}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    # outfit categories
    for key, cat_id, title in [
        ("jacket", "outfit.jacket", "Jacket"),
        ("footwear", "outfit.footwear", "Footwear"),
        ("gloves", "outfit.gloves", "Gloves"),
        ("cape", "outfit.cape", "Cape"),
    ]:
        items = migrate_outfit_map(text, key, cat_id, title)
        _write_category(CONTENT / "outfit_pack" / "tags" / f"{key}.yaml", cat_id, title, items)

    # fetish categories
    fetish_cats, conflict_groups = migrate_fetish_catalog(text)
    for cat_id, title, items in fetish_cats:
        _write_category(
            CONTENT / "fetish_pack" / "tags" / f"{cat_id}.yaml",
            f"fetish.{cat_id}",
            title,
            items,
        )

    conflict_payload = {
        "groups": [
            {
                "category_id": "fetish",
                "ids": ids,
                "reason": "FETISH_CONFLICT_GROUPS from eGen 8.6",
            }
            for ids in conflict_groups
        ]
    }
    (CONTENT / "fetish_pack" / "conflicts.yaml").write_text(
        yaml.dump(conflict_payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    skip_rules = migrate_external_skip(text)
    (CONTENT / "fetish_pack" / "external_skip.yaml").write_text(
        yaml.dump({"rules": skip_rules}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    print(f"locations: {len(loc_items)} items in {len(loc_groups)} groups")
    print(f"fetish categories: {len(fetish_cats)}")
    print(f"fetish conflict groups: {len(conflict_groups)}")
    print(f"external skip rules: {len(skip_rules)}")


if __name__ == "__main__":
    main()
