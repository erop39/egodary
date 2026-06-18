"""Tests for prompt import pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from egodary.api.main import app
from egodary.app import get_runtime_registry, reset_engine_cache
from egodary.bootstrap import build_app
from egodary.core.models import TagItem
from egodary.core.overlay_export import export_overlay_to_plugins_user
from egodary.core.runtime_registry import RuntimeRegistry
from egodary.prompting.prompt_analyze.extract_core import extract_core
from egodary.prompting.prompt_analyze.normalize_weights import normalize_weights
from egodary.prompting.prompt_import.classify_new_tags import classify_new_tags
from egodary.prompting.prompt_import.merge_to_registry import merge_to_registry
from egodary.prompting.prompt_import.parse_imported_prompt import parse_imported_prompt


def _runtime() -> RuntimeRegistry:
    base, _ = build_app()
    return RuntimeRegistry(base)


def test_normalize_weights_parses_paren():
    result = normalize_weights("1girl, (red dress:1.2), solo")
    assert result.had_weights
    assert any(t.text == "red dress" and t.weight == 1.2 for t in result.tokens)
    assert "red dress" in result.clean_prompt


def test_classify_dedupes_red_dress_against_core():
    core = extract_core("1girl, red dress, solo", "illustrious", _runtime())
    deduped, classified = classify_new_tags(["red dress"], core)
    assert len(deduped) == 1
    assert deduped[0].action == "merge_into_existing"
    assert not classified


def test_import_merge_adds_overlay_item():
    reg = _runtime()
    _, classified = classify_new_tags(["custom_unique_scarf_12345"], None)
    assert classified
    report = merge_to_registry(classified, reg, reprompt="1girl, custom_unique_scarf_12345")
    assert report.added
    assert reg.get_overlay_stats()["total"] >= 1


def test_import_merge_export_roundtrip(tmp_path):
    reg = _runtime()
    phrase = "zzq_unique_cape_marker_999"
    item = TagItem(
        id="imported_zzq_unique_cape",
        label="Unique Cape",
        tags={"illustrious": phrase, "anima": phrase, "zimage_turbo": phrase},
        meta={"subgroup": "imported", "source": "import"},
    )
    reg.add_item("appearance.accessories", item, source="import", original_phrase=phrase)
    paths = export_overlay_to_plugins_user(reg, pack_dir=tmp_path / "imported_pack")
    assert paths
    data = yaml.safe_load(paths[0].read_text(encoding="utf-8"))
    assert any(i["id"] == "imported_zzq_unique_cape" for i in data["items"])

    reg2 = RuntimeRegistry(build_app()[0])
    for item_data in data["items"]:
        loaded = TagItem.model_validate(item_data)
        reg2.add_item(data["id"], loaded, on_conflict="skip")

    parsed_overlay = parse_imported_prompt(f"1girl, {phrase}", "illustrious", reg2)
    parsed_base = parse_imported_prompt(f"1girl, {phrase}", "illustrious", build_app()[0])
    assert len(parsed_overlay.matched) > len(parsed_base.matched)
    assert any(m.matched_phrase == phrase for m in parsed_overlay.matched)


def test_api_prompt_import_merge():
    reset_engine_cache()
    client = TestClient(app)
    res = client.post(
        "/api/prompt/import/merge",
        json={"prompt": "1girl, solo, sunset", "model_id": "illustrious", "persist": False},
    )
    assert res.status_code == 200
    body = res.json()
    assert "state" in body
    assert "merge_report" in body


def test_api_prompt_import_classify_stores_resolution_status():
    reset_engine_cache()
    client = TestClient(app)
    phrase = "qqq_unique_import_phrase_5566"
    res = client.post(
        "/api/prompt/import/classify",
        json={"prompt": f"1girl, {phrase}", "model_id": "illustrious", "use_ollama": False},
    )
    assert res.status_code == 200, res.text
    rows = client.get("/api/unknown-tags?status=pending&limit=100").json()
    hit = next((row for row in rows if row.get("token") == phrase), None)
    assert hit is not None
    assert hit.get("suggested_subcategory") is not None or hit.get("suggested_subgroup") is not None
    assert hit.get("resolution_status") is not None


def test_api_prompt_analyze_convert():
    reset_engine_cache()
    client = TestClient(app)
    res = client.post(
        "/api/prompt/analyze/convert",
        json={
            "prompt": "1girl, solo, anime style",
            "model_id": "illustrious",
            "source_model": "illustrious",
            "target_model": "anima",
        },
    )
    assert res.status_code == 200
    assert res.json()["positive"]


def test_api_prompt_analyze_convert_to_json():
    reset_engine_cache()
    client = TestClient(app)
    res = client.post(
        "/api/prompt/analyze/convert",
        json={
            "prompt": "1girl, solo, masterpiece, best quality, sunset",
            "model_id": "illustrious",
            "source_model": "illustrious",
            "target_model": "json",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["format"] == "json"
    assert body["prompt_json"]["version"] == "1.2"
    assert body["prompt_json"]["model_target"] == "illustrious"
    subjects = body["prompt_json"]["positive"]["subjects"]
    assert isinstance(subjects, list) and len(subjects) >= 1
    assert "scene" in body["prompt_json"]["positive"]
    assert "negative" in body["prompt_json"]
    assert "parameters" in body["prompt_json"]
