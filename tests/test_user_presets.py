"""API tests for scoped user presets."""

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


SAMPLE_CAMERA_PAYLOAD = {
    "angle": "eye_level",
    "framing": "portrait",
    "lens": "85mm_portrait",
    "composition": "rule_of_thirds",
}


def test_user_presets_crud(client):
    empty = client.get("/api/user-presets?scope=camera")
    assert empty.status_code == 200
    assert empty.json() == []

    created = client.post(
        "/api/user-presets",
        json={
            "scope": "camera",
            "name": "My portrait",
            "payload": SAMPLE_CAMERA_PAYLOAD,
            "hint": "Eye Level + Portrait + 85mm",
        },
    )
    assert created.status_code == 200
    preset_id = created.json()["id"]

    listed = client.get("/api/user-presets?scope=camera")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["name"] == "My portrait"
    assert listed.json()[0]["field_count"] == 4

    detail = client.get(f"/api/user-presets/{preset_id}")
    assert detail.status_code == 200
    assert detail.json()["payload"] == SAMPLE_CAMERA_PAYLOAD

    renamed = client.put(
        f"/api/user-presets/{preset_id}",
        json={"name": "Renamed portrait"},
    )
    assert renamed.status_code == 200

    detail = client.get(f"/api/user-presets/{preset_id}")
    assert detail.json()["name"] == "Renamed portrait"

    deleted = client.delete(f"/api/user-presets/{preset_id}")
    assert deleted.status_code == 200

    missing = client.get(f"/api/user-presets/{preset_id}")
    assert missing.status_code == 404


def test_user_presets_reject_empty_name(client):
    resp = client.post(
        "/api/user-presets",
        json={"scope": "camera", "name": "   ", "payload": SAMPLE_CAMERA_PAYLOAD},
    )
    assert resp.status_code == 400
