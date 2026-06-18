"""API tests for favorite prompts."""

from __future__ import annotations

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


SAMPLE_SETTINGS = {
    "sampler": "Euler a",
    "schedule": "Karras",
    "steps": 28,
    "cfg": 7.0,
    "seed": 123456,
    "width": 832,
    "height": 1216,
    "hires": {
        "enabled": True,
        "scale": 2.0,
        "steps": 20,
        "denoising": 0.35,
        "upscaler": "4x-UltraSharp",
    },
}


def test_favorites_crud(client):
    empty = client.get("/api/favorites")
    assert empty.status_code == 200
    assert empty.json() == []

    created = client.post(
        "/api/favorites",
        json={
            "name": "Test Prompt",
            "positive": "1girl, masterpiece",
            "negative": "lowres",
            "model_id": "illustrious",
            "result_url": "https://example.com/img.png",
            "generation_settings": SAMPLE_SETTINGS,
        },
    )
    assert created.status_code == 200
    favorite_id = created.json()["id"]
    assert isinstance(favorite_id, int)

    listed = client.get("/api/favorites")
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["name"] == "Test Prompt"
    assert rows[0]["model_id"] == "illustrious"
    assert rows[0]["result_url"] == "https://example.com/img.png"
    assert rows[0]["generation_settings"]["steps"] == 28
    assert rows[0]["generation_settings"]["hires"]["enabled"] is True

    detail = client.get(f"/api/favorites/{favorite_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["positive"] == "1girl, masterpiece"
    assert body["negative"] == "lowres"
    assert body["generation_settings"]["sampler"] == "Euler a"
    assert body["generation_settings"]["seed"] == 123456

    updated = client.put(
        f"/api/favorites/{favorite_id}",
        json={
            "name": "Test Prompt Updated",
            "positive": "1girl, cinematic lighting",
            "negative": "lowres, blur",
            "model_id": "anima",
            "result_url": "https://example.com/new.png",
            "generation_settings": {"steps": 32, "seed": 777},
        },
    )
    assert updated.status_code == 200
    assert updated.json() == {"ok": True}

    detail_after = client.get(f"/api/favorites/{favorite_id}")
    assert detail_after.status_code == 200
    changed = detail_after.json()
    assert changed["name"] == "Test Prompt Updated"
    assert changed["model_id"] == "anima"
    assert changed["result_url"] == "https://example.com/new.png"
    assert changed["generation_settings"]["steps"] == 32
    assert changed["generation_settings"]["seed"] == 777

    deleted = client.delete(f"/api/favorites/{favorite_id}")
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True}

    missing = client.get(f"/api/favorites/{favorite_id}")
    assert missing.status_code == 404


def test_favorites_rejects_empty_name(client):
    res = client.post(
        "/api/favorites",
        json={"name": "   ", "positive": "test", "model_id": "anima"},
    )
    assert res.status_code == 400


def test_models_generation_defaults(client):
    res = client.get("/api/models/generation-defaults")
    assert res.status_code == 200
    data = res.json()
    assert "illustrious" in data
    assert "anima" in data
    assert "zimage_turbo" in data
    assert data["illustrious"]["defaults"]["steps"] > 0
    assert "hires" in data["illustrious"]
