import pytest

from egodary.core.models import ConflictGroup, TagCategory, TagItem
from egodary.core.registry import RegistryConflictError, TagRegistry


def _category(category_id: str, item_id: str = "item_a") -> TagCategory:
    return TagCategory(
        id=category_id,
        title=category_id,
        items=[TagItem(id=item_id, label=item_id, tags={"illustrious": item_id})],
    )


def test_register_and_get_category() -> None:
    registry = TagRegistry()
    registry.register_category(_category("scene.time_of_day"), source_plugin="pack_a")

    category = registry.get_category("scene.time_of_day")
    assert category is not None
    assert category.items[0].id == "item_a"
    assert registry.source_of("scene.time_of_day") == "pack_a"


def test_duplicate_category_id_raises() -> None:
    registry = TagRegistry()
    registry.register_category(_category("scene.time_of_day"), source_plugin="pack_a")

    with pytest.raises(RegistryConflictError):
        registry.register_category(_category("scene.time_of_day"), source_plugin="pack_b")


def test_summary_counts() -> None:
    registry = TagRegistry()
    registry.register_category(_category("scene.time_of_day"), source_plugin="pack_a")
    registry.register_conflict_group(ConflictGroup(category_id="scene.time_of_day", ids=["a", "b"]))

    summary = registry.summary()
    assert summary["category_count"] == 1
    assert summary["tag_count"] == 1
    assert summary["conflict_group_count"] == 1
