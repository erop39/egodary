"""Тесты для Wildcards — пользовательских текстовых списков тегов."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Парсинг (egodary.core.wildcards)
# ---------------------------------------------------------------------------

class TestWildcardParsing:
    def test_slugify_basic(self):
        from egodary.core.wildcards import slugify

        assert slugify("Long layered hair with curtain bangs") == "long_layered_hair_with_curtain_bangs"

    def test_slugify_strips_punctuation(self):
        from egodary.core.wildcards import slugify

        assert slugify("Blunt-cut bob (short)") == "blunt_cut_bob_short"

    def test_slugify_handles_ampersand(self):
        from egodary.core.wildcards import slugify

        assert slugify("Face & framing layers") == "face_and_framing_layers"

    def test_slugify_empty_string_fallback(self):
        from egodary.core.wildcards import slugify

        assert slugify("   ") == "item"
        assert slugify("***") == "item"

    def test_parse_wildcard_lines_strips_bullets(self):
        from egodary.core.wildcards import parse_wildcard_lines

        raw = "* Long layered hair\n- Textured lob\n• Blunt cut bob\nNo bullet line"
        lines = parse_wildcard_lines(raw)
        assert lines == ["Long layered hair", "Textured lob", "Blunt cut bob", "No bullet line"]

    def test_parse_wildcard_lines_skips_empty(self):
        from egodary.core.wildcards import parse_wildcard_lines

        raw = "Line one\n\n   \nLine two\n"
        assert parse_wildcard_lines(raw) == ["Line one", "Line two"]

    def test_make_item_id_unique_within_set(self):
        from egodary.core.wildcards import make_item_id

        used = {"blunt_cut_bob"}
        assert make_item_id("Blunt cut bob", used) == "blunt_cut_bob_2"

    def test_parse_wildcard_file_full_list(self):
        from egodary.core.wildcards import parse_wildcard_file

        raw = "\n".join([
            "Long layered hair with curtain bangs",
            "Textured lob with curtain bangs",
            "Blunt cut bob",
        ])
        parsed = parse_wildcard_file(raw, subgroup="trendy_2026")
        assert len(parsed) == 3
        labels = [label for label, _ in parsed]
        assert labels == [
            "Long layered hair with curtain bangs",
            "Textured lob with curtain bangs",
            "Blunt cut bob",
        ]
        ids = [item.id for _, item in parsed]
        assert ids == [
            "long_layered_hair_with_curtain_bangs",
            "textured_lob_with_curtain_bangs",
            "blunt_cut_bob",
        ]
        # All ids unique
        assert len(set(ids)) == len(ids)

    def test_parse_wildcard_file_dedupes_duplicate_lines(self):
        from egodary.core.wildcards import parse_wildcard_file

        raw = "Blunt cut bob\nBlunt cut bob\nBlunt cut bob"
        parsed = parse_wildcard_file(raw)
        ids = [item.id for _, item in parsed]
        assert ids == ["blunt_cut_bob", "blunt_cut_bob_2", "blunt_cut_bob_3"]

    def test_build_tag_item_sets_subgroup_meta(self):
        from egodary.core.wildcards import build_tag_item

        item = build_tag_item("Blunt cut bob", "blunt_cut_bob", subgroup="trendy_2026")
        assert item.meta["source"] == "wildcard"
        assert item.meta["subcategory_id"] == "trendy_2026"
        assert item.meta["subgroup"] == "trendy_2026"

    def test_build_tag_item_has_all_model_variants(self):
        from egodary.core.wildcards import build_tag_item

        item = build_tag_item("Blunt cut bob", "blunt_cut_bob")
        assert "illustrious" in item.tags
        assert "anima" in item.tags
        assert "zimage_turbo" in item.tags


# ---------------------------------------------------------------------------
# Persistence (egodary.persistence.schema)
# ---------------------------------------------------------------------------

class TestWildcardPersistence:
    @pytest.fixture(autouse=True)
    def _isolated_db(self, tmp_path, monkeypatch):
        from egodary.persistence import db as db_module

        db_path = tmp_path / "test.db"
        monkeypatch.setattr(db_module, "DB_PATH", db_path)
        yield

    def test_create_and_list_wildcards(self):
        from egodary.persistence.schema import create_wildcard, list_wildcards

        wid = create_wildcard(
            filename="hair.txt",
            label="Trendy Hairstyles",
            target_category="appearance.hair",
            target_subgroup="trendy_2026",
            raw_text="Blunt cut bob\nLong wavy hair",
            items=[("blunt_cut_bob", "Blunt cut bob"), ("long_wavy_hair", "Long wavy hair")],
        )
        assert wid > 0
        rows = list_wildcards()
        assert len(rows) == 1
        assert rows[0]["filename"] == "hair.txt"
        assert rows[0]["item_count"] == 2
        assert rows[0]["enabled"] == 1

    def test_get_wildcard_and_items(self):
        from egodary.persistence.schema import create_wildcard, get_wildcard, list_wildcard_items

        wid = create_wildcard(
            filename="hair.txt",
            label="Hair",
            target_category="appearance.hair",
            target_subgroup="trendy",
            raw_text="A\nB",
            items=[("a", "A"), ("b", "B")],
        )
        wildcard = get_wildcard(wid)
        assert wildcard["target_category"] == "appearance.hair"

        items = list_wildcard_items(wid)
        assert [i["item_id"] for i in items] == ["a", "b"]
        assert all(i["enabled"] == 1 for i in items)

    def test_set_wildcard_enabled(self):
        from egodary.persistence.schema import create_wildcard, get_wildcard, set_wildcard_enabled

        wid = create_wildcard(
            filename="hair.txt", label="Hair", target_category="appearance.hair",
            target_subgroup="trendy", raw_text="A", items=[("a", "A")],
        )
        assert set_wildcard_enabled(wid, False) is True
        assert get_wildcard(wid)["enabled"] == 0
        assert set_wildcard_enabled(wid, True) is True
        assert get_wildcard(wid)["enabled"] == 1

    def test_set_wildcard_enabled_not_found(self):
        from egodary.persistence.schema import set_wildcard_enabled

        assert set_wildcard_enabled(999, False) is False

    def test_set_wildcard_item_enabled(self):
        from egodary.persistence.schema import (
            create_wildcard,
            list_wildcard_items,
            set_wildcard_item_enabled,
        )

        wid = create_wildcard(
            filename="hair.txt", label="Hair", target_category="appearance.hair",
            target_subgroup="trendy", raw_text="A\nB", items=[("a", "A"), ("b", "B")],
        )
        assert set_wildcard_item_enabled(wid, "a", False) is True
        items = list_wildcard_items(wid)
        item_a = next(i for i in items if i["item_id"] == "a")
        assert item_a["enabled"] == 0

    def test_delete_wildcard_cascades_items(self):
        from egodary.persistence.schema import (
            create_wildcard,
            delete_wildcard,
            list_wildcard_items,
            list_wildcards,
        )

        wid = create_wildcard(
            filename="hair.txt", label="Hair", target_category="appearance.hair",
            target_subgroup="trendy", raw_text="A", items=[("a", "A")],
        )
        assert delete_wildcard(wid) is True
        assert list_wildcards() == []
        assert list_wildcard_items(wid) == []

    def test_load_wildcards_into_registry_only_enabled(self):
        from egodary.core.registry import TagRegistry
        from egodary.core.runtime_registry import RuntimeRegistry
        from egodary.persistence.schema import (
            create_wildcard,
            load_wildcards_into_registry,
            set_wildcard_item_enabled,
        )

        wid = create_wildcard(
            filename="hair.txt", label="Hair", target_category="appearance.hair",
            target_subgroup="trendy", raw_text="A\nB",
            items=[("a", "A"), ("b", "B")],
        )
        set_wildcard_item_enabled(wid, "b", False)

        registry = RuntimeRegistry(TagRegistry())
        loaded = load_wildcards_into_registry(registry)
        assert loaded == 1  # only "a" — "b" disabled

        category = registry.get_category("appearance.hair")
        assert category is not None
        ids = [i.id for i in category.items]
        # Registry ids are namespaced by wildcard id so that identical phrase
        # text in two different uploaded files can never collide and get
        # silently skipped — see load_wildcards_into_registry() docstring.
        assert f"wc{wid}_a" in ids
        assert f"wc{wid}_b" not in ids

    def test_load_wildcards_into_registry_two_files_same_text_dont_collide(self):
        """Regression test: two different uploaded wildcard files containing
        an identical line (same slugified item_id) must NOT cause one file's
        tag to silently disappear via the registry's on_conflict='skip'."""
        from egodary.core.registry import TagRegistry
        from egodary.core.runtime_registry import RuntimeRegistry
        from egodary.persistence.schema import create_wildcard, load_wildcards_into_registry

        wid_a = create_wildcard(
            filename="fileA.txt", label="fileA.txt", target_category="appearance.hair",
            target_subgroup="imported", raw_text="Long bangs",
            items=[("long_bangs", "Long bangs")],
        )
        wid_b = create_wildcard(
            filename="fileB.txt", label="fileB.txt", target_category="appearance.hair",
            target_subgroup="imported", raw_text="Long bangs",
            items=[("long_bangs", "Long bangs")],
        )
        assert wid_a != wid_b

        registry = RuntimeRegistry(TagRegistry())
        loaded = load_wildcards_into_registry(registry)
        assert loaded == 2  # both lines loaded, none skipped

        category = registry.get_category("appearance.hair")
        ids = [i.id for i in category.items]
        assert f"wc{wid_a}_long_bangs" in ids
        assert f"wc{wid_b}_long_bangs" in ids

    def test_load_wildcards_into_registry_skips_disabled_wildcard(self):
        from egodary.core.registry import TagRegistry
        from egodary.core.runtime_registry import RuntimeRegistry
        from egodary.persistence.schema import (
            create_wildcard,
            load_wildcards_into_registry,
            set_wildcard_enabled,
        )

        wid = create_wildcard(
            filename="hair.txt", label="Hair", target_category="appearance.hair",
            target_subgroup="trendy", raw_text="A", items=[("a", "A")],
        )
        set_wildcard_enabled(wid, False)

        registry = RuntimeRegistry(TagRegistry())
        loaded = load_wildcards_into_registry(registry)
        assert loaded == 0


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

class TestWildcardApi:
    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        from egodary.persistence import db as db_module
        from egodary import app as app_module

        monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.db")
        app_module.reset_engine_cache()

        from fastapi.testclient import TestClient
        from egodary.api.main import app as fastapi_app

        yield TestClient(fastapi_app)
        app_module.reset_engine_cache()

    def test_upload_wildcard(self, client):
        r = client.post("/api/wildcards", json={
            "filename": "hair.txt",
            "target_category": "appearance.hair",
            "target_subgroup": "trendy_2026",
            "raw_text": "Long layered hair with curtain bangs\nBlunt cut bob",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["item_count"] == 2
        assert data["target_category"] == "appearance.hair"

    def test_upload_wildcard_unknown_category_404(self, client):
        r = client.post("/api/wildcards", json={
            "filename": "x.txt",
            "target_category": "does.not.exist",
            "target_subgroup": "x",
            "raw_text": "A",
        })
        assert r.status_code == 404

    def test_upload_wildcard_empty_text_400(self, client):
        r = client.post("/api/wildcards", json={
            "filename": "x.txt",
            "target_category": "appearance.hair",
            "target_subgroup": "x",
            "raw_text": "   \n  \n",
        })
        assert r.status_code == 400

    def test_list_wildcards_after_upload(self, client):
        client.post("/api/wildcards", json={
            "filename": "hair.txt",
            "target_category": "appearance.hair",
            "target_subgroup": "trendy",
            "raw_text": "A\nB",
        })
        r = client.get("/api/wildcards")
        assert r.status_code == 200
        assert len(r.json()["wildcards"]) == 1

    def test_wildcard_detail(self, client):
        upload = client.post("/api/wildcards", json={
            "filename": "hair.txt",
            "target_category": "appearance.hair",
            "target_subgroup": "trendy",
            "raw_text": "A\nB",
        }).json()
        r = client.get(f"/api/wildcards/{upload['id']}")
        assert r.status_code == 200
        assert len(r.json()["items"]) == 2

    def test_wildcard_detail_not_found(self, client):
        r = client.get("/api/wildcards/999")
        assert r.status_code == 404

    def test_uploaded_tags_appear_in_category(self, client):
        upload = client.post("/api/wildcards", json={
            "filename": "hair.txt",
            "target_category": "appearance.hair",
            "target_subgroup": "trendy_2026",
            "raw_text": "Long layered hair with curtain bangs",
        }).json()
        r = client.get("/api/categories/appearance.hair")
        items = r.json()["items"]
        wc_items = [i for i in items if i.get("meta", {}).get("source") == "wildcard"]
        assert len(wc_items) == 1
        assert wc_items[0]["id"] == f"wc{upload['id']}_long_layered_hair_with_curtain_bangs"

    def test_uploaded_tag_used_in_generate(self, client):
        upload = client.post("/api/wildcards", json={
            "filename": "hair.txt",
            "target_category": "appearance.hair",
            "target_subgroup": "trendy_2026",
            "raw_text": "Long layered hair with curtain bangs",
        }).json()
        item_id = f"wc{upload['id']}_long_layered_hair_with_curtain_bangs"
        r = client.post("/api/generate", json={
            "model_id": "illustrious",
            "appearance": {"hair": item_id},
        })
        assert r.status_code == 200
        assert "long layered hair with curtain bangs" in r.json()["positive"].lower()

    def test_toggle_wildcard_off_removes_from_category(self, client):
        upload = client.post("/api/wildcards", json={
            "filename": "hair.txt",
            "target_category": "appearance.hair",
            "target_subgroup": "trendy",
            "raw_text": "Blunt cut bob",
        }).json()

        r = client.post(f"/api/wildcards/{upload['id']}/toggle", json={"enabled": False})
        assert r.status_code == 200
        assert r.json()["enabled"] is False

        cat = client.get("/api/categories/appearance.hair").json()
        wc_items = [i for i in cat["items"] if i.get("meta", {}).get("source") == "wildcard"]
        assert wc_items == []

    def test_toggle_wildcard_not_found(self, client):
        r = client.post("/api/wildcards/999/toggle", json={"enabled": False})
        assert r.status_code == 404

    def test_toggle_single_item(self, client):
        upload = client.post("/api/wildcards", json={
            "filename": "hair.txt",
            "target_category": "appearance.hair",
            "target_subgroup": "trendy",
            "raw_text": "Blunt cut bob\nLong wavy hair",
        }).json()

        r = client.post(f"/api/wildcards/{upload['id']}/items/blunt_cut_bob/toggle", json={"enabled": False})
        assert r.status_code == 200

        cat = client.get("/api/categories/appearance.hair").json()
        wc_ids = [i["id"] for i in cat["items"] if i.get("meta", {}).get("source") == "wildcard"]
        assert f"wc{upload['id']}_blunt_cut_bob" not in wc_ids
        assert f"wc{upload['id']}_long_wavy_hair" in wc_ids

    def test_toggle_item_not_found(self, client):
        upload = client.post("/api/wildcards", json={
            "filename": "hair.txt",
            "target_category": "appearance.hair",
            "target_subgroup": "trendy",
            "raw_text": "A",
        }).json()
        r = client.post(f"/api/wildcards/{upload['id']}/items/nonexistent/toggle", json={"enabled": False})
        assert r.status_code == 404

    def test_delete_wildcard(self, client):
        upload = client.post("/api/wildcards", json={
            "filename": "hair.txt",
            "target_category": "appearance.hair",
            "target_subgroup": "trendy",
            "raw_text": "A",
        }).json()

        r = client.delete(f"/api/wildcards/{upload['id']}")
        assert r.status_code == 200

        cat = client.get("/api/categories/appearance.hair").json()
        wc_items = [i for i in cat["items"] if i.get("meta", {}).get("source") == "wildcard"]
        assert wc_items == []

    def test_delete_wildcard_not_found(self, client):
        r = client.delete("/api/wildcards/999")
        assert r.status_code == 404

    def test_preview_endpoint(self, client):
        r = client.post("/api/wildcards/preview", json={
            "raw_text": "* Long layered hair\n* Blunt cut bob",
            "target_subgroup": "trendy",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 2
        assert data["items"][0]["item_id"] == "long_layered_hair"

    def test_two_wildcards_same_category_different_subgroups(self, client):
        client.post("/api/wildcards", json={
            "filename": "trendy.txt",
            "target_category": "appearance.hair",
            "target_subgroup": "trendy_2026",
            "raw_text": "Blunt cut bob",
        })
        client.post("/api/wildcards", json={
            "filename": "classic.txt",
            "target_category": "appearance.hair",
            "target_subgroup": "classic",
            "raw_text": "Ponytail",
        })
        cat = client.get("/api/categories/appearance.hair").json()
        wc_items = [i for i in cat["items"] if i.get("meta", {}).get("source") == "wildcard"]
        assert len(wc_items) == 2
        subgroups = {i["meta"]["subcategory_id"] for i in wc_items}
        assert subgroups == {"trendy_2026", "classic"}
