"""Generate pose_pack tag YAML files."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from catalog_pose_data import COUPLE_GROUPS, SOLO_GROUPS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1] / "egodary" / "content" / "pose_pack" / "tags"
RULES_PATH = Path(__file__).resolve().parents[1] / "egodary" / "content" / "pose_pack" / "pose_rules.yaml"


def slug(label: str) -> str:
    return (
        label.lower()
        .replace("(", "")
        .replace(")", "")
        .replace("'", "")
        .replace('"', "")
        .replace(",", "")
        .replace("/", " ")
        .replace("+", " ")
        .replace("&", " ")
        .replace("-", " ")
        .replace("  ", " ")
        .strip()
        .replace(" ", "_")
    )


def unique_id(label: str, subgroup: str, used: set[str]) -> str:
    base = slug(label)
    if base not in used:
        used.add(base)
        return base
    candidate = f"{subgroup}_{base}"
    if candidate not in used:
        used.add(candidate)
        return candidate
    index = 2
    while f"{candidate}_{index}" in used:
        index += 1
    final = f"{candidate}_{index}"
    used.add(final)
    return final


def pose_item(label: str, subgroup: str, used: set[str]) -> dict:
    item_id = unique_id(label, subgroup, used)
    ill = label.lower()
    return {
        "id": item_id,
        "label": label,
        "meta": {"subgroup": subgroup},
        "tags": {
            "illustrious": ill,
            "anima": f"{ill}, dynamic pose",
            "zimage_turbo": f"in {ill}",
        },
    }


def items_from_groups(groups: dict[str, list[str]], used: set[str]) -> list[dict]:
    items: list[dict] = []
    for subgroup, labels in groups.items():
        for label in labels:
            items.append(pose_item(label, subgroup, used))
    return items


def write_category(cat_id: str, title: str, items: list[dict]) -> None:
    path = ROOT / f"{cat_id.split('.')[-1]}.yaml"
    payload = {"id": cat_id, "title": title, "items": items}
    path.write_text(yaml.dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def write_pose_rules(couple_ids: list[str], solo_items: list[dict], couple_items: list[dict]) -> None:
    solo_subgroups: dict[str, list[str]] = {sg: [] for sg in SOLO_GROUPS}
    for item in solo_items:
        solo_subgroups[item["meta"]["subgroup"]].append(item["id"])
    couple_subgroups: dict[str, list[str]] = {sg: [] for sg in COUPLE_GROUPS}
    for item in couple_items:
        couple_subgroups[item["meta"]["subgroup"]].append(item["id"])
    payload = {
        "solo_category": "pose.solo",
        "couple_category": "pose.couple",
        "couple_pose_ids": couple_ids,
        "solo_subgroups": solo_subgroups,
        "couple_subgroups": couple_subgroups,
    }
    RULES_PATH.write_text(yaml.dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    used: set[str] = set()
    solo_items = items_from_groups(SOLO_GROUPS, used)
    couple_items = items_from_groups(COUPLE_GROUPS, used)
    write_category("pose.solo", "Solo Pose", solo_items)
    write_category("pose.couple", "Couple Pose", couple_items)
    write_pose_rules([item["id"] for item in couple_items], solo_items, couple_items)

    legacy = ROOT / "general.yaml"
    if legacy.is_file():
        legacy.unlink()

    print(f"Wrote {len(solo_items)} solo + {len(couple_items)} couple poses to {ROOT}")


if __name__ == "__main__":
    main()
