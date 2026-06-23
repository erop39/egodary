"""Tattoo bucket helpers — subgroup ordering for prompt assembly."""

from __future__ import annotations

from egodary.core.registry import TagRegistry
from egodary.core.runtime_registry import RuntimeRegistry

RegistryLike = TagRegistry | RuntimeRegistry

TATTOO_SUBGROUP_ORDER: tuple[str, ...] = (
    "styles",
    "placements",
    "themes",
    "specific",
    "temporary",
)


def tattoo_subgroup_rank(registry: RegistryLike, item_id: str) -> int:
    category = registry.get_category("appearance.tattoos")
    if not category:
        return len(TATTOO_SUBGROUP_ORDER)
    subgroup = ""
    for item in category.items:
        if item.id == item_id:
            subgroup = str(item.meta.get("subgroup") or item.meta.get("subcategory_id") or "")
            break
    try:
        return TATTOO_SUBGROUP_ORDER.index(subgroup)
    except ValueError:
        return len(TATTOO_SUBGROUP_ORDER)


def sort_tattoo_ids(registry: RegistryLike, tattoo_ids: list[str]) -> list[str]:
    return sorted(tattoo_ids, key=lambda item_id: (tattoo_subgroup_rank(registry, item_id), item_id))
