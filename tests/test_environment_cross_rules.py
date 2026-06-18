"""Tests for environment pack and cross-category compatibility rules."""

from egodary.bootstrap import build_app
from egodary.core.conflicts import apply_state_conflicts, preview_state_conflicts
from egodary.core.models import (
    CameraState,
    EnvironmentState,
    FetishState,
    LightingState,
    PromptState,
    SceneState,
)
from egodary.core.rule_matching import load_cross_rules


def test_environment_pack_loads_63_items():
    registry, _ = build_app()
    location = registry.get_category("environment.location")
    situation = registry.get_category("environment.situation")
    modifiers = registry.get_category("environment.modifiers")
    assert location is not None
    assert situation is not None
    assert modifiers is not None
    assert len(location.items) == 35
    assert len(situation.items) == 21
    assert len(modifiers.items) == 7
    assert len(location.items) + len(situation.items) + len(modifiers.items) == 63


def test_environment_location_groups_defined():
    from pathlib import Path

    import yaml

    path = (
        Path(__file__).resolve().parents[1]
        / "egodary"
        / "content"
        / "environment_pack"
        / "environment_rules.yaml"
    )
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    groups = data.get("location_groups") or {}
    assert "luxury" in groups
    assert "neon_cyberpunk" in groups
    assert "dungeon" in groups
    assert len(groups["luxury"]) >= 3


def test_cross_rules_loaded():
    data = load_cross_rules()
    penalties = data.get("penalties") or []
    bonuses = data.get("bonuses") or []
    assert len(penalties) >= 15
    assert len(bonuses) >= 3
    severities = {rule.get("severity") for rule in penalties}
    assert "hard_block" in severities
    assert "strong_warning" in severities
    assert "soft_warning" in severities


def test_cross_rule_luxury_heavy_fetish_warning():
    state = PromptState(
        environment=EnvironmentState(location="luxury_bedroom"),
        fetish=FetishState(elements=["collar_and_leash", "rope_bondage_shibari"]),
    )
    warnings = preview_state_conflicts(state)
    assert any("luxury" in w.lower() and "bdsm" in w.lower() for w in warnings)


def test_cross_rule_camera_close_full_hard_block():
    state = PromptState(
        camera=CameraState(
            framing="full_body",
            nsfw_shot="extreme_close_up_on_lips",
        ),
    )
    resolved, warnings = apply_state_conflicts(state)
    assert any("close-up" in w.lower() or "close up" in w.lower() for w in warnings)
    assert any("full body" in w.lower() for w in warnings)
    assert resolved.camera.nsfw_shot == ""


def test_cross_rule_neon_candle_conflict():
    state = PromptState(
        environment=EnvironmentState(location="neon_cyberpunk_street"),
        lighting=LightingState(light_type="candlelight"),
    )
    warnings = preview_state_conflicts(state)
    assert any("neon" in w.lower() and "candle" in w.lower() for w in warnings)


def test_environment_indoor_clears_weather():
    from egodary.app import create_engine

    engine = create_engine()
    state = PromptState(
        scene=SceneState(weather="rain", season="winter"),
        environment=EnvironmentState(location="modern_bedroom"),
    )
    result = engine.assemble(state)
    assert "rain" not in result.positive.lower()
    assert "winter" not in result.positive.lower()


def test_environment_tags_in_scene_bucket():
    from egodary.app import create_engine

    engine = create_engine()
    state = PromptState(
        environment=EnvironmentState(
            location="candlelit_room",
            modifiers=["heavy_fog"],
        ),
    )
    result = engine.assemble(state)
    text = result.positive.lower()
    assert "candlelit" in text or "candlelit room" in text
    assert "heavy fog" in text or "fog" in text


def test_fetish_too_many_elements_warning():
    state = PromptState(
        fetish=FetishState(
            elements=[
                "collar_and_leash",
                "rope_bondage_shibari",
                "chains",
                "blindfold",
                "ball_gag",
                "metal_handcuffs",
            ],
        ),
    )
    warnings = preview_state_conflicts(state)
    assert any("more than 5" in w.lower() or "trimmed to 5" in w.lower() for w in warnings)
