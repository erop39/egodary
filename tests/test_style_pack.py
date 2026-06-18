"""Tests for style pack loading and prompt integration."""

from egodary.bootstrap import build_app
from egodary.app import create_engine
from egodary.core.models import PromptState, StyleState


def test_style_pack_loads_categories():
    registry, _ = build_app()
    for cat_id in ("style.art_style", "style.artist_style", "style.quality", "style.aesthetic", "style.technique"):
        category = registry.get_category(cat_id)
        assert category is not None
        assert len(category.items) > 0


def test_style_off_removes_style_from_prompt():
    engine = create_engine()
    state = PromptState(
        model_id="illustrious",
        style=StyleState(
            enabled=False,
            art_style="anime_style",
            quality=["masterpiece"],
            quality_boosters_enabled=False,
        ),
    )
    result = engine.assemble(state)
    text = result.positive.lower()
    assert "masterpiece" not in text
    assert "anime style" not in text
    assert "score_9" not in text


def test_quality_boosters_not_applied_to_illustrious():
    engine = create_engine()
    state = PromptState(
        model_id="illustrious",
        style=StyleState(
            enabled=True,
            art_style="anime_style",
            quality_boosters_enabled=True,
            quality_boosters_level="high",
        ),
    )
    result = engine.assemble(state)
    assert not any(tag in {"score_9", "score_8_up", "score_7_up"} for tag in result.buckets.quality)
    assert "score_9" not in result.positive
    assert "score_8_up" not in result.positive
    assert "score_7_up" not in result.positive


def test_illustrious_strips_leaked_score_tags_from_quality_bucket():
    from egodary.core.quality_boosters import finalize_quality_bucket

    stripped = finalize_quality_bucket(
        ["score_9", "score_8_up", "masterpiece"],
        StyleState(quality_boosters_enabled=True, quality_boosters_level="high"),
        "illustrious",
    )
    assert stripped == ["masterpiece"]

    from egodary.core.models import PromptBuckets

    state = PromptState(
        model_id="illustrious",
        style=StyleState(enabled=True, quality=["masterpiece"]),
    )
    buckets = PromptBuckets(quality=["score_9", "score_8_up", "score_7_up", "masterpiece"])
    buckets.quality = finalize_quality_bucket(buckets.quality, state.style, "illustrious")
    assert buckets.quality == ["masterpiece"]


def test_quality_boosters_high_adds_score_tags():
    engine = create_engine()
    state = PromptState(
        model_id="anima",
        style=StyleState(
            enabled=False,
            quality_boosters_enabled=True,
            quality_boosters_level="high",
        ),
    )
    result = engine.assemble(state)
    assert result.buckets.quality[:3] == ["score_9", "score_8_up", "score_7_up"]
    assert "score_9" in result.positive


def test_quality_boosters_medium_and_low():
    engine = create_engine()

    medium = PromptState(
        model_id="anima",
        style=StyleState(quality_boosters_enabled=True, quality_boosters_level="medium"),
    )
    assert engine.assemble(medium).buckets.quality[:2] == ["score_8_up", "score_7_up"]

    low = PromptState(
        model_id="anima",
        style=StyleState(quality_boosters_enabled=True, quality_boosters_level="low"),
    )
    assert engine.assemble(low).buckets.quality[:1] == ["score_7_up"]


def test_quality_boosters_off_adds_no_scores():
    engine = create_engine()
    state = PromptState(
        model_id="anima",
        style=StyleState(
            enabled=True,
            art_style="anime_style",
            quality_boosters_enabled=False,
        ),
    )
    result = engine.assemble(state)
    assert not any(tag.startswith("score_") for tag in result.buckets.quality)


def test_style_on_adds_selected_tags():
    engine = create_engine()
    state = PromptState(
        model_id="illustrious",
        style=StyleState(
            enabled=True,
            art_style="anime_style",
            quality=["masterpiece", "best_quality"],
            aesthetic=["very_aesthetic"],
        ),
    )
    result = engine.assemble(state)
    text = result.positive.lower()
    assert "anime style" in text
    assert "masterpiece" in text
    assert "very aesthetic" in text
