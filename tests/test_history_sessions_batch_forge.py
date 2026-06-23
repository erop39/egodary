"""Tests for generation history, sessions, batch generate, and Forge integration."""

from __future__ import annotations

import json
from unittest.mock import patch

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


SAMPLE_STATE = {
    "model_id": "illustrious",
    "character": {},
    "outfit": {},
    "appearance": {},
    "face": {},
    "scene": {"time": "", "weather": "", "season": "", "location": ""},
    "environment": {"location": "", "situation": "", "modifiers": []},
    "pose": "",
    "camera": {},
    "lighting": {},
    "style": {"enabled": True, "art_style": "anime_style", "quality": [], "aesthetic": [],
               "technique": [], "quality_boosters_enabled": True, "quality_boosters_level": "high"},
}


# ---------------------------------------------------------------------------
# Generation history
# ---------------------------------------------------------------------------


def test_history_empty(client):
    resp = client.get("/api/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["history"] == []
    assert data["count"] == 0


def test_history_populated_after_generate(client):
    client.post("/api/generate", json=SAMPLE_STATE)
    resp = client.get("/api/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    entry = data["history"][0]
    assert "positive" in entry
    assert "model_id" in entry
    assert entry["model_id"] == "illustrious"
    assert "payload" in entry  # full state is included


def test_history_limit(client):
    for _ in range(5):
        client.post("/api/generate", json=SAMPLE_STATE)
    resp = client.get("/api/history?limit=3")
    assert resp.status_code == 200
    assert resp.json()["count"] == 3


def test_history_model_filter(client):
    client.post("/api/generate", json={**SAMPLE_STATE, "model_id": "anima"})
    client.post("/api/generate", json={**SAMPLE_STATE, "model_id": "illustrious"})
    resp = client.get("/api/history?model_id=anima")
    assert resp.status_code == 200
    data = resp.json()
    assert all(e["model_id"] == "anima" for e in data["history"])


def test_history_delete_entry(client):
    client.post("/api/generate", json=SAMPLE_STATE)
    entries = client.get("/api/history").json()["history"]
    entry_id = entries[0]["id"]
    resp = client.delete(f"/api/history/{entry_id}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert client.get("/api/history").json()["count"] == 0


def test_history_delete_nonexistent(client):
    assert client.delete("/api/history/9999").status_code == 404


def test_history_clear_all(client):
    for _ in range(3):
        client.post("/api/generate", json=SAMPLE_STATE)
    resp = client.delete("/api/history")
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 3
    assert client.get("/api/history").json()["count"] == 0


def test_history_clear_by_model(client):
    client.post("/api/generate", json={**SAMPLE_STATE, "model_id": "anima"})
    client.post("/api/generate", json={**SAMPLE_STATE, "model_id": "illustrious"})
    resp = client.delete("/api/history?model_id=anima")
    assert resp.status_code == 200
    remaining = client.get("/api/history").json()["history"]
    assert all(e["model_id"] == "illustrious" for e in remaining)


def test_history_limit_validation(client):
    assert client.get("/api/history?limit=0").status_code == 422
    assert client.get("/api/history?limit=201").status_code == 422


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


def test_sessions_empty(client):
    resp = client.get("/api/sessions")
    assert resp.status_code == 200
    assert resp.json()["sessions"] == []


def test_sessions_save_and_list(client):
    resp = client.post("/api/sessions", json={"name": "My session", "state": SAMPLE_STATE})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    session_id = data["id"]

    listing = client.get("/api/sessions").json()["sessions"]
    assert len(listing) == 1
    assert listing[0]["name"] == "My session"
    assert listing[0]["id"] == session_id


def test_sessions_get_full_state(client):
    client.post("/api/sessions", json={"name": "Full", "state": SAMPLE_STATE})
    session_id = client.get("/api/sessions").json()["sessions"][0]["id"]

    resp = client.get(f"/api/sessions/{session_id}")
    assert resp.status_code == 200
    session = resp.json()["session"]
    assert session["state"]["model_id"] == "illustrious"


def test_sessions_get_nonexistent(client):
    assert client.get("/api/sessions/9999").status_code == 404


def test_sessions_rename(client):
    client.post("/api/sessions", json={"name": "Old name", "state": SAMPLE_STATE})
    session_id = client.get("/api/sessions").json()["sessions"][0]["id"]

    resp = client.patch(f"/api/sessions/{session_id}", json={"name": "New name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New name"

    updated = client.get(f"/api/sessions/{session_id}").json()["session"]
    assert updated["name"] == "New name"


def test_sessions_rename_nonexistent(client):
    assert client.patch("/api/sessions/9999", json={"name": "X"}).status_code == 404


def test_sessions_delete(client):
    client.post("/api/sessions", json={"name": "To delete", "state": SAMPLE_STATE})
    session_id = client.get("/api/sessions").json()["sessions"][0]["id"]

    resp = client.delete(f"/api/sessions/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert client.get("/api/sessions").json()["sessions"] == []


def test_sessions_delete_nonexistent(client):
    assert client.delete("/api/sessions/9999").status_code == 404


def test_sessions_empty_name_rejected(client):
    resp = client.post("/api/sessions", json={"name": "  ", "state": SAMPLE_STATE})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Batch generate
# ---------------------------------------------------------------------------


def test_batch_returns_correct_count(client):
    resp = client.post("/api/generate/batch", json={"state": SAMPLE_STATE, "count": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 3
    assert len(data["results"]) == 3


def test_batch_result_shape(client):
    resp = client.post("/api/generate/batch", json={"state": SAMPLE_STATE, "count": 1})
    result = resp.json()["results"][0]
    assert "positive" in result
    assert "negative" in result
    assert "model_id" in result
    assert "quality_score" in result
    assert "varied_state" in result


def test_batch_count_clamped_to_8(client):
    resp = client.post("/api/generate/batch", json={"state": SAMPLE_STATE, "count": 99})
    assert resp.status_code == 200
    assert resp.json()["count"] == 8


def test_batch_count_minimum_1(client):
    resp = client.post("/api/generate/batch", json={"state": SAMPLE_STATE, "count": 0})
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


def test_batch_saves_to_history(client):
    client.post("/api/generate/batch", json={"state": SAMPLE_STATE, "count": 3})
    history = client.get("/api/history").json()
    assert history["count"] == 3


def test_batch_explicit_axes(client):
    resp = client.post("/api/generate/batch", json={
        "state": SAMPLE_STATE,
        "count": 2,
        "randomize_axes": ["time", "season"],
    })
    assert resp.status_code == 200
    for result in resp.json()["results"]:
        assert "time" in result["varied_state"]
        assert "season" in result["varied_state"]


# ---------------------------------------------------------------------------
# Forge settings
# ---------------------------------------------------------------------------


def test_forge_settings_defaults(client):
    resp = client.get("/api/forge/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False
    assert "base_url" in data
    assert "default_steps" in data


def test_forge_settings_update(client):
    resp = client.put("/api/forge/settings", json={"enabled": True, "default_steps": 30})
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is True
    assert data["default_steps"] == 30
    # persisted
    assert client.get("/api/forge/settings").json()["default_steps"] == 30


def test_forge_health_disabled(client):
    resp = client.post("/api/forge/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert "disabled" in data["error"].lower()


def test_forge_send_disabled(client):
    resp = client.post("/api/forge/send", json={"positive": "1girl", "negative": ""})
    assert resp.status_code == 400
    assert "disabled" in resp.json()["detail"].lower()


def test_forge_send_enabled_but_unreachable(client):
    # Use a tiny gen_timeout so the TCP attempt fails fast instead of waiting 10s
    client.put("/api/forge/settings", json={"enabled": True, "base_url": "http://127.0.0.1:19999", "gen_timeout": 0.05})
    resp = client.post("/api/forge/send", json={"positive": "1girl", "negative": ""})
    assert resp.status_code == 502


def test_forge_send_mocked_success(client):
    client.put("/api/forge/settings", json={"enabled": True})
    mock_result = {
        "ok": True,
        "images": ["base64data"],
        "parameters": {"prompt": "1girl"},
        "info": {"seed": 42},
        "error": None,
    }
    with patch("egodary.integrations.forge.send_to_forge", return_value=mock_result):
        resp = client.post("/api/forge/send", json={"positive": "1girl", "negative": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["images"] == ["base64data"]
    assert data["info"]["seed"] == 42
