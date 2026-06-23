"""API tests for character library presets."""

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


SAMPLE_PAYLOAD = {
    "character": {
        "age_appearance": "young_adult",
        "body_type": "curvy",
        "breast_size": "large",
        "breast_shape": "",
        "waist": "slim",
        "hips_ass": "wide",
        "legs": "long",
        "overall_figure": "",
        "height_build": "tall",
        "ethnicity": "asian",
        "skin_tone": "fair",
        "body_details": ["abs"],
    },
    "face": {
        "facial_expression": "seductive",
        "mouth_lips": "full_lips",
        "eyes": "large_eyes",
        "skin": "",
        "face_shape": "oval",
        "eyebrows": "",
        "nose": "",
        "jaw_chin": "",
        "age_maturity": "",
        "beauty_archetype": "",
        "facial_details": "",
    },
    "appearance": {"hair": "long_straight"},
}


def test_character_library_crud(client):
    empty = client.get("/api/character-library")
    assert empty.status_code == 200
    assert empty.json() == []

    created = client.post(
        "/api/character-library",
        json={"name": "Test Hero", "payload": SAMPLE_PAYLOAD},
    )
    assert created.status_code == 200
    preset_id = created.json()["id"]
    assert isinstance(preset_id, int)

    listed = client.get("/api/character-library")
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["name"] == "Test Hero"
    assert rows[0]["field_count"] >= 10

    detail = client.get(f"/api/character-library/{preset_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["name"] == "Test Hero"
    assert body["payload"]["character"]["body_type"] == "curvy"
    assert body["payload"]["face"]["eyes"] == "large_eyes"
    assert body["payload"]["appearance"]["hair"] == "long_straight"

    deleted = client.delete(f"/api/character-library/{preset_id}")
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True}

    missing = client.get(f"/api/character-library/{preset_id}")
    assert missing.status_code == 404


def test_character_library_rename(client):
    created = client.post(
        "/api/character-library",
        json={"name": "Rename Me", "payload": SAMPLE_PAYLOAD},
    )
    assert created.status_code == 200
    preset_id = created.json()["id"]

    renamed = client.patch(
        f"/api/character-library/{preset_id}",
        json={"name": "Renamed Hero"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Renamed Hero"

    missing = client.patch(
        "/api/character-library/999999",
        json={"name": "Ghost"},
    )
    assert missing.status_code == 404


def test_character_library_rejects_empty_name(client):
    res = client.post(
        "/api/character-library",
        json={"name": "   ", "payload": SAMPLE_PAYLOAD},
    )
    assert res.status_code == 400


def test_character_library_accepts_legacy_array_scalars(client):
    payload = {
        **SAMPLE_PAYLOAD,
        "character": {
            **SAMPLE_PAYLOAD["character"],
            "age_appearance": ["young_adult"],
            "body_type": ["curvy"],
            "breast_shape": ["firm_breasts", "round_breasts"],
        },
    }
    res = client.post(
        "/api/character-library",
        json={"name": "Legacy Arrays", "payload": payload},
    )
    assert res.status_code == 200, res.text
    preset_id = res.json()["id"]
    detail = client.get(f"/api/character-library/{preset_id}")
    assert detail.status_code == 200
    assert detail.json()["payload"]["character"]["body_type"] == "curvy"
    assert detail.json()["payload"]["character"]["age_appearance"] == "young_adult"
