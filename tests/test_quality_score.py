"""Tests for the 0–100 quality score system."""

from __future__ import annotations

from egodary.core.models import CameraState, EnvironmentState, FetishState, LightingState, PromptState
from egodary.core.quality_score import compute_quality_score


def test_perfect_combo_scores_excellent():
    result = compute_quality_score(PromptState())
    assert result.score >= 90
    assert result.level == "Отлично"
    assert not result.issues


def test_ecu_full_body_hard_penalty():
    state = PromptState(
        camera=CameraState(
            framing="full_body",
            nsfw_shot="extreme_close_up_on_lips",
        ),
    )
    result = compute_quality_score(state)
    assert 50 <= result.score <= 55
    assert any(issue.severity == "hard" for issue in result.issues)
    assert any("Full Body" in issue.message for issue in result.issues)


def test_multiple_conflicts_compound():
    state = PromptState(
        camera=CameraState(
            angle="low_angle",
            framing="extreme_close_up_face_eyes_lips",
            lens="24mm_wide_angle",
        ),
    )
    result = compute_quality_score(state)
    assert result.score < 75
    assert len(result.issues) >= 2


def test_synergy_bonus_increases_score():
    state = PromptState(
        lighting=LightingState(
            light_type="low_key_lighting",
            direction="rim_lighting",
        ),
        fetish=FetishState(elements=["collar_and_leash"]),
    )
    result = compute_quality_score(state)
    assert result.score == 100
    assert any(bonus.tier == "good" for bonus in result.bonuses)


def test_fetish_overload_penalty():
    elements = [
        "collar_and_leash",
        "leather_cuffs",
        "silk_ropes",
        "rope_bondage_shibari",
        "chains",
        "harness_restraints",
        "mind_break",
    ]
    state = PromptState(fetish=FetishState(elements=elements))
    result = compute_quality_score(state)
    assert result.score < 90
    assert any(issue.severity == "overload" for issue in result.issues)


def test_excellent_submissive_dungeon_combo():
    from egodary.core.models import FaceState

    state = PromptState(
        environment=EnvironmentState(location="basement__dungeon"),
        camera=CameraState(angle="high_angle"),
        face=FaceState(facial_expression="submissive__obedient_look"),
        fetish=FetishState(elements=["collar_and_leash"]),
    )
    result = compute_quality_score(state)
    assert any(bonus.tier == "excellent" for bonus in result.bonuses)


def test_quality_preview_endpoint():
    from egodary.api.main import preview_quality

    state = PromptState(camera=CameraState(framing="full_body", nsfw_shot="extreme_close_up_on_lips"))
    payload = preview_quality(state)
    assert payload["score"] == compute_quality_score(state).score
    assert payload["level"] in ("Отлично", "Хорошо", "Средне", "Плохо", "Очень плохо")
