"""Tests for Illustrious prompt assembly and generation rules."""

from egodary.app import create_engine
from egodary.core.models import (
    EnvironmentState,
    FaceState,
    PromptState,
    StyleState,
)
from egodary.core.rules_loader import get_model_gen_rules, invalidate_rules_cache


def test_illustrious_rules_bucket_order():
    invalidate_rules_cache()
    rules = get_model_gen_rules("illustrious")
    order = rules.format["bucket_order"]
    assert order.index("quality") < order.index("subject") < order.index("character")
    assert order.index("subject") < order.index("face") < order.index("outfit")
    assert order.index("face") < order.index("hair") < order.index("makeup")
    assert order.index("pose") < order.index("scene") < order.index("lighting")
    assert order.index("style") < order.index("fetish") < order.index("extra")
    assert rules.format.get("technical_suffix")


def test_illustrious_tag_order_subject_pose_environment_style():
    engine = create_engine()
    state = PromptState(
        model_id="illustrious",
        style=StyleState(
            enabled=True,
            art_style="anime_style",
            artist_style="moebius_style",
            quality=["masterpiece"],
            aesthetic=["sultry"],
        ),
        face=FaceState(facial_expression="drunk_on_pleasure"),
        environment=EnvironmentState(
            location="basement__dungeon",
            situation="suspended",
        ),
        pose="confident_standing_hand_on_hip_chest_forward",
    )
    result = engine.assemble(state)
    parts = [p.strip() for p in result.positive.split(",")]

    assert parts.index("masterpiece") < parts.index("1girl") < parts.index("drunk on pleasure")
    assert parts.index("1girl") < parts.index("confident standing")
    assert parts.index("confident standing") < parts.index("suspended")
    assert parts.index("suspended") < parts.index("basement / dungeon")
    assert parts.index("basement / dungeon") < parts.index("anime style")
    assert parts.index("anime style") < parts.index("sultry")
    assert parts[-2:] == ["clean anatomy", "coherent composition"]
    assert result.buckets.situation == ["suspended"]
    assert "basement" in " ".join(result.buckets.scene).lower()


def test_illustrious_dedupes_case_insensitive():
    from egodary.core.models import PromptBuckets
    from egodary.models_adapters.prompt_format import format_buckets_as_tag_string

    buckets = PromptBuckets(quality=["Masterpiece", "masterpiece", "best quality"])
    text = format_buckets_as_tag_string(
        buckets,
        bucket_order=["quality"],
        dedupe_tags=True,
        tag_case="lower",
    )
    assert text.count("masterpiece") == 1
