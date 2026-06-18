"""Tests for JSON → model renderers and unified convert pipeline."""

from __future__ import annotations

from egodary.app import reset_engine_cache
from egodary.bootstrap import build_app
from egodary.core.pipeline import PromptEngine
from egodary.core.runtime_registry import RuntimeRegistry
from egodary.prompting.prompt_analyze.convert_to_model import convert_analyze
from egodary.prompting.prompt_analyze.json_to_model import render_illustrious


SAMPLE_JSON = {
    "version": "1.2",
    "model_target": "illustrious",
    "positive": {
        "subjects": [
            {
                "description": "1girl, solo, beautiful woman, long silver hair",
                "position": "standing near window",
                "action": "looking outside",
                "expression": "soft smile",
                "clothing": "white shirt",
            }
        ],
        "scene": {
            "location": "apartment",
            "time_of_day": "evening",
            "weather": "rain",
            "environment_details": "city lights",
        },
        "style": {
            "art_style": "anime illustration",
            "artist": "",
            "rendering": "soft shading",
            "quality_tags": ["masterpiece", "best quality"],
        },
        "lighting": "soft warm light",
        "camera": {
            "shot_type": "medium shot",
            "angle": "three-quarter view",
            "lens": "85mm",
            "depth_of_field": "shallow depth of field",
        },
        "composition": "rule of thirds",
        "mood": "calm, melancholic",
        "color_palette": ["cool blues", "warm amber"],
    },
    "nsfw": {"intensity": "low", "focus": []},
    "negative": {
        "general": ["blurry", "low quality"],
        "anatomy": ["bad hands"],
        "artifacts": ["grainy"],
    },
    "parameters": {"steps": 30, "cfg_scale": 7, "sampler": "Euler a", "seed": -1, "width": 1024, "height": 1024},
}


def _engine() -> PromptEngine:
    base, _ = build_app()
    return PromptEngine(RuntimeRegistry(base))


def test_render_illustrious_from_json_order():
    positive, negative = render_illustrious(SAMPLE_JSON)
    assert positive.index("masterpiece") < positive.index("1girl")
    assert "rain" in positive
    assert "soft warm light" in positive
    assert "bad hands" in negative


def test_convert_analyze_illustrious_to_anima_uses_json_pipeline():
    reset_engine_cache()
    engine = _engine()
    result = convert_analyze(
        prompt="1girl, solo, anime style, masterpiece",
        source_model="illustrious",
        target_model="anima",
        engine=engine,
    )
    assert result.format == "text"
    assert result.prompt_json["version"] == "1.2"
    assert "\n\n" in (result.positive or "")
    assert result.positive


def test_convert_analyze_json_input_to_illustrious():
    reset_engine_cache()
    engine = _engine()
    import json

    result = convert_analyze(
        prompt=json.dumps(SAMPLE_JSON),
        source_model="illustrious",
        target_model="illustrious",
        engine=engine,
    )
    assert result.detected_format == "json"
    assert "1girl" in (result.positive or "")
    assert "masterpiece" in (result.positive or "")


def test_convert_analyze_target_json():
    reset_engine_cache()
    engine = _engine()
    result = convert_analyze(
        prompt="1girl, solo, sunset",
        source_model="illustrious",
        target_model="json",
        engine=engine,
    )
    assert result.format == "json"
    assert result.prompt_json["positive"]["subjects"]


def test_convert_to_json_from_tags():
    from egodary.prompting.prompt_analyze.convert_to_json import convert_to_json

    reset_engine_cache()
    engine = _engine()
    payload, detected = convert_to_json(
        prompt="1girl, solo, masterpiece, standing, sunset",
        source_model="illustrious",
        engine=engine,
    )
    assert detected in {"tags", "weighted_tags", "unknown"}
    assert payload["version"] == "1.2"
    assert payload["positive"]["subjects"]
