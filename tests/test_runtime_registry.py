"""Tests for RuntimeRegistry overlay."""

from __future__ import annotations

from egodary.bootstrap import build_app
from egodary.core.models import TagItem
from egodary.core.runtime_registry import RuntimeRegistry


def _registry() -> RuntimeRegistry:
    base, _ = build_app()
    return RuntimeRegistry(base)


def test_add_item_and_resolve():
    reg = _registry()
    item = TagItem(
        id="imported_test_tag",
        label="Test",
        tags={"illustrious": "test tag phrase", "anima": "test tag phrase"},
        meta={"subgroup": "imported"},
    )
    result = reg.add_item("outfit.dress", item, source="import")
    assert result.action == "added"
    assert reg.resolve_tag("outfit.dress", result.item_id, "illustrious") == "test tag phrase"
    cat = reg.get_category("outfit.dress")
    assert any(i.id == result.item_id for i in cat.items)


def test_conflict_rename():
    reg = _registry()
    item = TagItem(id="dup_id", label="A", tags={"illustrious": "a"})
    reg.add_item("prompting.imported", item, source="import")
    second = TagItem(id="dup_id", label="B", tags={"illustrious": "b"})
    result = reg.add_item("prompting.imported", second, source="import", on_conflict="rename")
    assert result.action == "renamed"
    assert result.item_id != "dup_id"


def test_conflict_skip():
    reg = _registry()
    item = TagItem(id="skip_id", label="A", tags={"illustrious": "a"})
    reg.add_item("prompting.imported", item, source="user")
    second = TagItem(id="skip_id", label="B", tags={"illustrious": "b"})
    result = reg.add_item("prompting.imported", second, on_conflict="skip")
    assert result.action == "skipped"


def test_clear_overlay_and_stats():
    reg = _registry()
    reg.add_item(
        "prompting.imported",
        TagItem(id="x1", label="X", tags={"illustrious": "x"}),
        source="import",
    )
    reg.add_item(
        "prompting.imported",
        TagItem(id="x2", label="Y", tags={"illustrious": "y"}),
        source="manual",
    )
    stats = reg.get_overlay_stats()
    assert stats["total"] == 2
    assert stats["by_source"]["import"] == 1
    removed = reg.clear_overlay(source="import")
    assert removed == 1
    assert reg.get_overlay_stats()["total"] == 1


def test_remove_item():
    reg = _registry()
    reg.add_item(
        "prompting.imported",
        TagItem(id="rm", label="R", tags={"illustrious": "r"}),
    )
    assert reg.remove_item("prompting.imported", "rm")
    assert reg.get_overlay_stats()["total"] == 0


def test_virtual_category_from_overlay_only():
    reg = _registry()
    reg.add_item(
        "prompting.imported",
        TagItem(id="only_overlay", label="O", tags={"illustrious": "only"}),
    )
    cat = reg.get_category("prompting.imported")
    assert cat is not None
    assert cat.id == "prompting.imported"
    assert len(cat.items) == 1


def test_get_category_overlay_replaces_core_with_same_id():
    reg = _registry()
    cat_before = reg.get_category("outfit.dress")
    assert cat_before and cat_before.items
    core = cat_before.items[0]
    count_before = len(cat_before.items)
    overlay = TagItem(
        id=core.id,
        label=core.label,
        tags=dict(core.tags),
        meta={**(core.meta or {}), "description": "overlay replaces core"},
    )
    reg.add_item("outfit.dress", overlay, source="user", on_conflict="overwrite")
    cat_after = reg.get_category("outfit.dress")
    assert len(cat_after.items) == count_before
    assert sum(1 for item in cat_after.items if item.id == core.id) == 1
    replaced = next(item for item in cat_after.items if item.id == core.id)
    assert replaced.meta.get("description") == "overlay replaces core"
