"""API tests for debug and changelog endpoints."""

from fastapi.testclient import TestClient

from egodary.api.main import app


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
