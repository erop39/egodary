from egodary.core.models import TagItem
from egodary.persistence.schema import (
    list_runtime_tag_items,
    migrate_runtime_subgroup_to_subcategory,
    rollback_runtime_subcategory_to_subgroup,
    save_runtime_tag_item,
)


def test_runtime_migration_backfills_subcategory_and_normalized_name():
    item = TagItem(
        id="migration_marker_item",
        label="Migration Marker Label",
        tags={"illustrious": "migration marker"},
        meta={"subgroup": "legacy_subgroup"},
    )
    save_runtime_tag_item("prompting.imported", item, source="user")
    result = migrate_runtime_subgroup_to_subcategory(status="active")
    assert result["scanned"] >= 1

    rows = list_runtime_tag_items(limit=200)
    hit = next((row for row in rows if row.get("item_id") == "migration_marker_item"), None)
    assert hit is not None
    meta = (hit.get("item") or {}).get("meta") or {}
    assert meta.get("subgroup") == "legacy_subgroup"
    assert meta.get("subcategory_id") == "legacy_subgroup"
    assert meta.get("normalized_name") == "migration marker label"


def test_runtime_migration_rollback_removes_subcategory_id():
    item = TagItem(
        id="rollback_marker_item",
        label="Rollback Marker",
        tags={"illustrious": "rollback marker"},
        meta={"subgroup": "legacy_rb"},
    )
    save_runtime_tag_item("prompting.imported", item, source="user")
    migrate_runtime_subgroup_to_subcategory(status="active")
    result = rollback_runtime_subcategory_to_subgroup(status="active")
    assert result["scanned"] >= 1

    rows = list_runtime_tag_items(limit=200)
    hit = next((row for row in rows if row.get("item_id") == "rollback_marker_item"), None)
    assert hit is not None
    meta = (hit.get("item") or {}).get("meta") or {}
    assert meta.get("subgroup") == "legacy_rb"
    assert "subcategory_id" not in meta
