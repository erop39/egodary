"""Tests for LLM settings persistence and health/API behavior."""

from __future__ import annotations

import io
import urllib.request
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from egodary.api.main import app
from egodary.app import get_llm_settings, reset_engine_cache, update_llm_settings
from egodary.core.llm_settings import LlmHealthReport, LlmSettings
from egodary.integrations import ollama
from egodary.persistence.schema import load_llm_settings, save_llm_settings


def test_llm_settings_round_trip_sqlite():
    settings = LlmSettings(
        enabled=True,
        base_url="http://127.0.0.1:11434",
        model="qwen2.5:7b",
        temperature=0.2,
        top_p=0.8,
        timeout=12.0,
        max_retries=2,
        health_ttl_seconds=33,
        last_health=LlmHealthReport(ok=True, reachable=True, model_listed=True, json_probe_ok=True),
        last_health_at=datetime.now(timezone.utc),
    )
    save_llm_settings(settings)
    loaded = load_llm_settings()
    assert loaded.enabled is True
    assert loaded.model == "qwen2.5:7b"
    assert loaded.timeout == 12.0
    assert loaded.max_retries == 2
    assert loaded.last_health is not None
    assert loaded.last_health.ok is True


def test_check_ollama_health_ok(monkeypatch):
    settings = LlmSettings(enabled=True, model="llama3.1")

    def fake_request(url, *, method="GET", payload=None, timeout=30.0):
        if url.endswith("/api/tags"):
            return {"models": [{"name": "llama3.1"}]}
        if url.endswith("/api/chat"):
            return {"message": {"content": '{"ok": true}'}}
        raise AssertionError("unexpected url")

    monkeypatch.setattr(ollama, "_request_json", fake_request)
    health = ollama.check_ollama_health(settings, force=True)
    assert health.ok is True
    assert health.reachable is True
    assert health.model_listed is True
    assert health.json_probe_ok is True


def test_check_ollama_health_model_missing(monkeypatch):
    settings = LlmSettings(enabled=True, model="missing-model")

    def fake_request(url, *, method="GET", payload=None, timeout=30.0):
        if url.endswith("/api/tags"):
            return {"models": [{"name": "llama3.1"}]}
        return {"message": {"content": '{"ok": true}'}}

    monkeypatch.setattr(ollama, "_request_json", fake_request)
    health = ollama.check_ollama_health(settings, force=True)
    assert health.ok is False
    assert health.model_listed is False
    assert "not installed" in (health.error or "")


def test_check_ollama_health_model_alias(monkeypatch):
    settings = LlmSettings(enabled=True, model="llama3")

    def fake_request(url, *, method="GET", payload=None, timeout=30.0):
        if url.endswith("/api/tags"):
            return {"models": [{"name": "llama3:latest"}]}
        if url.endswith("/api/chat"):
            return {"message": {"content": '{"ok": true}'}}
        raise AssertionError("unexpected url")

    monkeypatch.setattr(ollama, "_request_json", fake_request)
    health = ollama.check_ollama_health(settings, force=True)
    assert health.ok is True
    assert health.model_listed is True


def test_parse_json_content_handles_fenced_json():
    assert ollama._parse_json_content('```json\n{"ok": true}\n```') == {"ok": True}


def test_urlopen_bypasses_proxy_for_localhost(monkeypatch):
    captured: dict[str, object] = {}

    class FakeOpener:
        def open(self, req, timeout=30.0):
            captured["url"] = req.full_url
            return urllib.request.addinfourl(io.BytesIO(b"{}"), {}, req.full_url)

    import urllib.request

    monkeypatch.setattr(
        urllib.request,
        "build_opener",
        lambda *args, **kwargs: FakeOpener(),
    )

    def fail_default(*args, **kwargs):
        raise AssertionError("default urlopen should not be used for localhost")

    monkeypatch.setattr(urllib.request, "urlopen", fail_default)
    req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
    ollama._urlopen(req, timeout=5.0)
    assert captured["url"] == "http://127.0.0.1:11434/api/tags"


def test_api_put_get_llm_settings():
    reset_engine_cache()
    client = TestClient(app)
    res_put = client.put(
        "/api/llm/settings",
        json={
            "enabled": False,
            "base_url": "http://127.0.0.1:11434",
            "model": "llama3",
            "temperature": 0.3,
            "top_p": 0.9,
            "timeout": 15,
            "max_retries": 1,
            "health_ttl_seconds": 45,
        },
    )
    assert res_put.status_code == 200
    res_get = client.get("/api/llm/settings")
    assert res_get.status_code == 200
    body = res_get.json()
    assert body["settings"]["model"] == "llama3"
    assert "health" in body


def test_nsfw_returns_400_when_llm_unhealthy(monkeypatch):
    reset_engine_cache()
    update_llm_settings(LlmSettings(enabled=True, model="llama3"))
    client = TestClient(app)

    def fake_cached_health(settings, force=False):
        return LlmHealthReport(ok=False, error="model unavailable")

    import egodary.api.main as api_main

    monkeypatch.setattr(api_main, "get_cached_health", fake_cached_health)
    res = client.post(
        "/api/prompt/nsfw-style",
        json={
            "prompt": "1girl, red dress, sunset",
            "model_id": "illustrious",
            "intensity": "medium",
            "use_llm": True,
        },
    )
    assert res.status_code == 400
    assert "model unavailable" in res.text


def test_ollama_enabled_reflects_runtime_settings():
    update_llm_settings(LlmSettings(enabled=True))
    assert ollama.ollama_enabled() is True
    update_llm_settings(LlmSettings(enabled=False))
    assert ollama.ollama_enabled() is False

