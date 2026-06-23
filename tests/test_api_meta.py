"""API tests for debug and changelog endpoints."""

import pytest
from fastapi.testclient import TestClient

from egodary.api.main import app
from egodary.persistence import db


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    monkeypatch.setattr(db, "DB_PATH", db_path)
    return db_path


@pytest.fixture
def client(temp_db):
    return TestClient(app)


def test_api_debug_snapshot():
    client = TestClient(app)
    res = client.get("/api/debug")
    assert res.status_code == 200
    data = res.json()
    assert data["app_version"]
    assert data["registry"]["category_count"] >= 10
    assert "face" in data["category_prefixes"]


def test_api_character_categories():
    from egodary.app import reset_engine_cache

    reset_engine_cache()
    client = TestClient(app)
    res = client.get("/api/categories/character.body_type")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "character.body_type"
    assert len(data["items"]) >= 10


def test_api_preview_accepts_legacy_corrupt_payload():
    from egodary.app import reset_engine_cache

    reset_engine_cache()
    client = TestClient(app)
    payload = {
        "model_id": "illustrious",
        "character": {"body_type": ["curvy"], "body_details": None},
        "lighting": {"quality": []},
        "style": {"quality": None, "aesthetic": None, "technique": None},
        "appearance": {"makeup": None},
        "fetish": {"elements": None},
        "outfit": {"conditions": None},
    }
    for path in ("/api/conflicts/preview", "/api/quality/preview", "/api/generate/preview"):
        res = client.post(path, json=payload)
        assert res.status_code == 200, res.text


def test_api_changelog():
    client = TestClient(app)
    res = client.get("/api/changelog")
    assert res.status_code == 200
    body = res.json()
    assert "markdown" in body
    assert "Changelog" in body["markdown"]


def test_api_add_runtime_tag_item():
    from egodary.app import reset_engine_cache

    reset_engine_cache()
    client = TestClient(app)
    res = client.post(
        "/api/categories/appearance.makeup/items",
        json={
            "label": "test neon eyeliner marker",
            "subgroup": "eyes",
            "persist": False,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["category_id"] == "appearance.makeup"
    assert body["item"]["overlay"] is True
    assert body["item"]["meta"]["subgroup"] == "eyes"
    assert body["item"]["meta"]["subcategory_id"] == "eyes"
    assert body["item"]["tags"]["illustrious"] == "test neon eyeliner marker"


def test_api_add_runtime_tag_item_rejects_invalid_subgroup():
    from egodary.app import reset_engine_cache

    reset_engine_cache()
    client = TestClient(app)
    res = client.post(
        "/api/categories/appearance.makeup/items",
        json={
            "label": "test invalid subgroup marker",
            "subgroup": "not_existing_subgroup",
            "persist": False,
        },
    )
    assert res.status_code == 400, res.text


def test_api_add_runtime_tag_item_supports_new_subcategory_when_enabled():
    from egodary.app import reset_engine_cache

    reset_engine_cache()
    client = TestClient(app)
    res = client.post(
        "/api/categories/prompting.imported/items",
        json={
            "label": "brand new subcategory tag marker",
            "subcategory_id": "custom_subcat",
            "allow_new_subcategory": True,
            "persist": False,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["item"]["meta"]["subcategory_id"] == "custom_subcat"
    assert body["item"]["meta"]["subgroup"] == "custom_subcat"


def test_api_add_runtime_tag_item_rejects_hard_duplicate():
    from egodary.app import reset_engine_cache

    reset_engine_cache()
    client = TestClient(app)
    first = client.post(
        "/api/categories/prompting.imported/items",
        json={
            "label": "duplicate label marker",
            "subcategory_id": "imported",
            "allow_new_subcategory": True,
            "persist": False,
        },
    )
    assert first.status_code == 200, first.text
    second = client.post(
        "/api/categories/prompting.imported/items",
        json={
            "label": "duplicate label marker",
            "subcategory_id": "imported",
            "allow_new_subcategory": True,
            "persist": False,
        },
    )
    assert second.status_code == 409, second.text


def test_api_tag_studio_update_and_deactivate_runtime_item():
    from egodary.app import reset_engine_cache

    reset_engine_cache()
    client = TestClient(app)
    created = client.post(
        "/api/categories/prompting.imported/items",
        json={
            "label": "updatable runtime marker",
            "subcategory_id": "imported",
            "allow_new_subcategory": True,
            "persist": False,
        },
    )
    assert created.status_code == 200, created.text
    item_id = created.json()["item"]["id"]

    updated = client.put(
        f"/api/categories/prompting.imported/items/{item_id}",
        json={
            "description": "updated by test",
            "aliases": ["runtime_alias_one", "runtime_alias_two"],
            "subcategory_id": "imported_2",
            "allow_new_subcategory": True,
            "persist": False,
        },
    )
    assert updated.status_code == 200, updated.text
    updated_item = updated.json()["item"]
    assert updated_item["meta"]["description"] == "updated by test"
    assert "runtime_alias_one" in updated_item["meta"]["aliases"]
    assert updated_item["meta"]["subcategory_id"] == "imported_2"

    deactivated = client.post(
        f"/api/categories/prompting.imported/items/{item_id}/deactivate?persist=false"
    )
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["item"]["meta"]["is_active"] is False


def test_api_update_core_tag_forks_to_runtime_overlay():
    from egodary.app import get_runtime_registry, reset_engine_cache

    reset_engine_cache()
    client = TestClient(app)
    registry = get_runtime_registry()
    category = registry.get_category("outfit.dress")
    assert category and category.items
    core = category.items[0]
    updated = client.put(
        f"/api/categories/outfit.dress/items/{core.id}",
        json={
            "description": "forked from core by test",
            "persist": False,
            "source": "user",
        },
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["item"]["meta"]["description"] == "forked from core by test"
    item, is_overlay = registry.find_item("outfit.dress", core.id)
    assert is_overlay
    assert item is not None
    assert item.meta.get("description") == "forked from core by test"
    merged = registry.get_category("outfit.dress")
    assert sum(1 for entry in merged.items if entry.id == core.id) == 1


def test_api_runtime_subcategory_migration_endpoint():
    client = TestClient(app)
    res = client.post("/api/tag-studio/migrate/runtime-subcategory", json={"status": "active"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert "scanned" in body
    assert "migrated" in body


def test_api_runtime_subcategory_rollback_endpoint():
    client = TestClient(app)
    res = client.post("/api/tag-studio/rollback/runtime-subcategory", json={"status": "active"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert "scanned" in body
    assert "rolled_back" in body


def test_api_tag_studio_items_search_and_deduplicate():
    from egodary.app import reset_engine_cache

    reset_engine_cache()
    client = TestClient(app)
    create_a = client.post(
        "/api/categories/prompting.imported/items",
        json={
            "label": "searchable neon marker",
            "subcategory_id": "imported",
            "allow_new_subcategory": True,
            "persist": False,
            "dedupe_policy": "allow",
        },
    )
    assert create_a.status_code == 200, create_a.text
    create_b = client.post(
        "/api/categories/prompting.imported/items",
        json={
            "label": "searchable neon markers",
            "subcategory_id": "imported",
            "allow_new_subcategory": True,
            "persist": False,
            "dedupe_policy": "allow",
        },
    )
    assert create_b.status_code == 200, create_b.text

    search = client.get("/api/tag-studio/items?q=neon marker&category_id=prompting.imported")
    assert search.status_code == 200, search.text
    payload = search.json()
    assert payload["count"] >= 1

    dedupe = client.get("/api/tag-studio/deduplicate?category_id=prompting.imported&fuzzy_threshold=0.8")
    assert dedupe.status_code == 200, dedupe.text
    assert "findings" in dedupe.json()


def test_api_tag_studio_alias_search():
    from egodary.app import reset_engine_cache

    reset_engine_cache()
    client = TestClient(app)
    created = client.post(
        "/api/categories/prompting.imported/items",
        json={
            "label": "primary label only",
            "aliases": ["wet ripped alias marker"],
            "subcategory_id": "imported",
            "allow_new_subcategory": True,
            "persist": False,
        },
    )
    assert created.status_code == 200, created.text

    by_alias = client.get("/api/tag-studio/items?q=ripped alias&category_id=prompting.imported")
    assert by_alias.status_code == 200, by_alias.text
    ids = {row["item"]["id"] for row in by_alias.json()["items"]}
    assert created.json()["item"]["id"] in ids


def test_api_tag_studio_reactivate_runtime_item():
    from egodary.app import reset_engine_cache

    reset_engine_cache()
    client = TestClient(app)
    created = client.post(
        "/api/categories/prompting.imported/items",
        json={
            "label": "reactivate marker",
            "subcategory_id": "imported",
            "allow_new_subcategory": True,
            "persist": False,
        },
    )
    assert created.status_code == 200, created.text
    item_id = created.json()["item"]["id"]
    deactivated = client.post(
        f"/api/categories/prompting.imported/items/{item_id}/deactivate?persist=false"
    )
    assert deactivated.status_code == 200, deactivated.text

    reactivated = client.put(
        f"/api/categories/prompting.imported/items/{item_id}",
        json={"is_active": True, "persist": False},
    )
    assert reactivated.status_code == 200, reactivated.text
    assert reactivated.json()["item"]["meta"]["is_active"] is True


def test_api_move_runtime_tag_item_into_brand_new_subcategory():
    """Move tag's destination subcategory must accept a subgroup name that has
    no tags in it yet. The Tag Studio "Move to subcategory" field used to be a
    closed <select> populated only from subcategories that already contain at
    least one item, so moving into an empty/new subgroup was silently
    impossible from the UI — even though this endpoint always supported it."""
    from egodary.app import reset_engine_cache

    reset_engine_cache()
    client = TestClient(app)
    created = client.post(
        "/api/categories/prompting.imported/items",
        json={
            "label": "move target marker",
            "subcategory_id": "imported",
            "allow_new_subcategory": True,
            "persist": False,
        },
    )
    assert created.status_code == 200, created.text
    item_id = created.json()["item"]["id"]

    moved = client.post(
        f"/api/categories/prompting.imported/items/{item_id}/move",
        json={
            "to_category_id": "prompting.imported",
            "to_subcategory_id": "brand_new_empty_subgroup",
            "persist": False,
        },
    )
    assert moved.status_code == 200, moved.text

    cat = client.get("/api/categories/prompting.imported").json()
    moved_item = next((i for i in cat["items"] if i["id"] == item_id), None)
    assert moved_item is not None
    assert moved_item["meta"]["subcategory_id"] == "brand_new_empty_subgroup"
    assert moved_item["meta"]["subgroup"] == "brand_new_empty_subgroup"


def test_api_advanced_todo_roundtrip(client):
    empty = client.get("/api/advanced/todo")
    assert empty.status_code == 200
    assert empty.json() == {"items": []}

    saved = client.put(
        "/api/advanced/todo",
        json={
            "items": [
                {
                    "id": "t1",
                    "text": "Ship clothing states",
                    "done": False,
                    "priority": "high",
                    "due_date": "2099-01-01",
                    "sort_order": 0,
                    "created_at": "2026-06-19T00:00:00Z",
                }
            ]
        },
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["priority"] == "high"

    loaded = client.get("/api/advanced/todo")
    assert loaded.status_code == 200
    assert loaded.json()["items"][0]["text"] == "Ship clothing states"
