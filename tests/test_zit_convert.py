"""Tests for Z-Image Turbo convert v1.1."""

from __future__ import annotations

from fastapi.testclient import TestClient

from egodary.api.main import app
from egodary.app import reset_engine_cache
from egodary.bootstrap import build_app
from egodary.core.pipeline import PromptEngine
from egodary.core.runtime_registry import RuntimeRegistry
from egodary.prompting.prompt_analyze.convert_to_model import convert_analyze
from egodary.prompting.prompt_analyze.zit_lexicon import classify_token, is_meta_quality, is_subject_count
from egodary.prompting.prompt_analyze.zit_renderer import render_zimage_turbo_v11
from egodary.prompting.prompt_analyze.zit_semantics import extract_zit_semantics

GALLERY_PROMPT = (
    "masterpiece, best quality, realistic, detailed skin, highres, uncensored, 1girl, elegant, "
    "medium breasts, big lips, long straight red hair, neat bangs, clear green eyes, smooth skin, "
    "graceful silhouette, modest proportions, smile, calm expression, she looks closely at the painting "
    "and touches her chin, classic white long dress, soft fabric flowing, wide red satin ribbon, "
    "delicate gloves, side view, upper body focus, dutch angle, dynamic pose, art gallery interior, "
    "white walls, soft spotlight, framed abstract paintings, muted color palette, soft bloom"
)


def _engine() -> PromptEngine:
    base, _ = build_app()
    return PromptEngine(RuntimeRegistry(base))


def test_lexicon_classifies_meta_and_count():
    assert is_meta_quality("masterpiece")
    assert is_subject_count("1girl")
    assert is_subject_count("solo")
    from egodary.prompting.prompt_analyze.zit_lexicon import TokenClass

    assert classify_token("cat ears") == TokenClass.APPEARANCE_FEATURE
    assert classify_token("collar") == TokenClass.ACCESSORY


def test_gallery_convert_strips_meta_tags():
    reset_engine_cache()
    engine = _engine()
    result = convert_analyze(
        prompt=GALLERY_PROMPT,
        source_model="illustrious",
        target_model="zimage_turbo",
        engine=engine,
    )
    text = (result.positive or "").lower()
    assert "masterpiece" not in text
    assert "best quality" not in text
    assert "1girl" not in text
    assert "solo" not in text
    assert "highres" not in text
    assert result.zit_semantics is not None
    assert result.zit_paragraphs


def test_gallery_paragraph_order_lighting_before_camera():
    reset_engine_cache()
    engine = _engine()
    result = convert_analyze(
        prompt=GALLERY_PROMPT,
        source_model="illustrious",
        target_model="zimage_turbo",
        engine=engine,
    )
    paragraphs = result.zit_paragraphs
    lighting_idx = next(i for i, p in enumerate(paragraphs) if "lighting" in p.lower())
    camera_idx = next(i for i, p in enumerate(paragraphs) if "composition" in p.lower() or "upper body" in p.lower())
    assert lighting_idx < camera_idx


def test_hair_color_conflict_recorded():
    reset_engine_cache()
    engine = _engine()
    result = convert_analyze(
        prompt="1girl, solo, long red hair, blonde hair, blue eyes, green eyes",
        source_model="illustrious",
        target_model="zimage_turbo",
        engine=engine,
    )
    conflicts = result.zit_semantics.get("conflicts") or []
    fields = {c.get("field") for c in conflicts}
    assert "hair_color" in fields or "eye_color" in fields


def test_creature_and_accessory_routing():
    semantics = extract_zit_semantics(
        {
            "version": "1.2",
            "positive": {
                "subjects": [
                    {
                        "description": "1girl, solo, cat ears, collar, partially unbuttoned shirt",
                        "attributes": {"count_tags": ["1girl", "solo"]},
                    }
                ],
                "style": {"quality_tags": [], "art_style": "", "artist": "", "rendering": ""},
            },
            "nsfw": {"focus": ["wet skin"]},
        }
    )
    appearance = " ".join(semantics.appearance).lower()
    outfit = " ".join(semantics.outfit).lower()
    nsfw = " ".join(semantics.nsfw_neutral).lower()
    assert "cat ears" in appearance
    assert "collar" in outfit
    assert "unbuttoned" in nsfw or "wet skin" in nsfw


def test_count_tags_in_json_attributes():
    reset_engine_cache()
    engine = _engine()
    result = convert_analyze(
        prompt="1girl, solo, sunset, masterpiece",
        source_model="illustrious",
        target_model="json",
        engine=engine,
    )
    subjects = result.prompt_json["positive"]["subjects"]
    assert "1girl" in subjects[0]["attributes"]["count_tags"]
    assert "solo" in subjects[0]["attributes"]["count_tags"]
    assert "1girl" not in subjects[0]["description"]


def test_api_zit_convert_response_fields():
    reset_engine_cache()
    client = TestClient(app)
    res = client.post(
        "/api/prompt/analyze/convert",
        json={
            "prompt": GALLERY_PROMPT,
            "model_id": "illustrious",
            "source_model": "illustrious",
            "target_model": "zimage_turbo",
            "use_llm": False,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["format"] == "text"
    assert "zit_semantics" in body
    assert "zit_paragraphs" in body
    assert body["used_llm"] is False
    assert "masterpiece" not in body["positive"].lower()


def test_render_line_present():
    result = render_zimage_turbo_v11(
        {
            "version": "1.2",
            "positive": {
                "subjects": [{"description": "red hair, smile", "attributes": {"count_tags": ["1girl", "solo"]}}],
                "style": {"art_style": "realistic", "quality_tags": [], "artist": "", "rendering": ""},
            },
        }
    )
    assert result.paragraphs[-1].lower().startswith("the image has")
