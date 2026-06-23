import pytest

from egodary.app import create_engine
from egodary.bootstrap import build_app
from egodary.core.converter import convert_prompt
from egodary.core.importer import import_prompt_with_report
from egodary.core.models import CameraState, PromptState, SceneState, TagCategory, TagItem
from egodary.core.registry import RegistryConflictError, TagRegistry


def test_core_tags_loaded_in_registry():
    registry, _ = build_app()
    assert registry.get_category("scene.time") is not None
    assert registry.get_category("scene.weather") is not None
    assert registry.get_category("camera.angle") is not None


def test_registry_resolve_tag():
    registry, _ = build_app()
    tag = registry.resolve_tag("scene.time", "sunset", "illustrious")
    assert tag is not None
    assert "sunset" in tag


def test_prompt_engine_assemble():
    from egodary.core.models import StyleState

    engine = create_engine()
    state = PromptState(
        model_id="illustrious",
        style=StyleState(enabled=True, art_style="", quality=["masterpiece", "best_quality"]),
        scene=SceneState(time="sunset", weather="clear_sky"),
        camera=CameraState(angle="low_angle"),
    )
    result = engine.assemble(state)
    assert "sunset" in result.positive
    assert "clear sky" in result.positive
    assert "low angle" in result.positive.lower() or "from below" in result.positive
    assert result.negative is not None
    assert "masterpiece" in result.positive
    assert "best quality" in result.positive


def test_anima_block_format():
    from egodary.core.models import StyleState

    engine = create_engine()
    state = PromptState(
        model_id="anima",
        style=StyleState(enabled=True, art_style="anime_style", quality=["masterpiece", "best_quality"]),
        scene=SceneState(time="night"),
    )
    result = engine.assemble(state)
    assert "\n\n" in result.positive
    assert "masterpiece" in result.positive
    assert "score_7" in result.positive
    assert "night" in result.positive.lower()
    assert result.positive.count("\n\n") >= 10


def test_anima_dedupes_boilerplate_and_limits_lighting():
    from egodary.core.models import (
        AppearanceState,
        CameraState,
        CharacterState,
        FaceState,
        LightingState,
        OutfitState,
        PromptState,
        SceneState,
        StyleState,
    )

    engine = create_engine()
    state = PromptState(
        model_id="anima",
        style=StyleState(enabled=True, art_style="anime_style", quality=["masterpiece", "best_quality"]),
        character=CharacterState(body_type="athletic__toned", age_appearance="31_35"),
        appearance=AppearanceState(
            hair="long_slicked_back_wet",
            makeup=["extreme_blush__gloss", "dewy__glossy_skin"],
            accessories=["o_ring_choker"],
        ),
        face=FaceState(
            facial_expression="slight_smirk_half_lidded_eyes",
            eyes="narrow_calculating_eyes",
            beauty_archetype="elegant_mature_beauty",
        ),
        outfit=OutfitState(
            top="extreme_micro_crop",
            bottom="wetlook_micro_panties",
            legwear="neon_green_thigh_high_socks",
            conditions={"top": {"damage": "torn_ripped"}},
        ),
        pose="gripping_thighs_while_spreading",
        camera=CameraState(
            framing="full_body_with_space",
            focus="sharp_focus_on_face",
            nsfw_shot="high_angle_submission_shot",
        ),
        lighting=LightingState(
            light_type="dramatic_cinematic_lighting",
            direction="strong_side_lighting_dramatic_shadows",
            color_mood="warm_golden_lighting",
            nsfw="back_lighting_on_silhouette",
        ),
        scene=SceneState(time="morning", weather="rain", season="summer"),
    )
    result = engine.assemble(state)
    text = result.positive.lower()
    blocks = result.positive.split("\n\n")

    assert text.count("detailed face") == 1
    assert ", cinematic lighting" not in text
    assert text.count("cinematic framing") == 0
    assert text.count("styled outfit") == 0
    assert text.count("face makeup") == 0
    assert "full body" not in text
    assert "31" in text
    assert "athletic" in text
    lighting_block = blocks[10]
    assert len([part for part in lighting_block.split(",") if part.strip()]) <= 2


def test_anima_face_expression_and_artist_style_blocks():
    from egodary.core.models import FaceState, StyleState

    engine = create_engine()
    state = PromptState(
        model_id="anima",
        style=StyleState(
            enabled=True,
            art_style="anime_style",
            artist_style="alfonso_azpiri_style",
            quality=["masterpiece", "best_quality"],
            aesthetic=["lewd"],
        ),
        face=FaceState(facial_expression="drunk_on_pleasure"),
    )
    result = engine.assemble(state)
    blocks = result.positive.split("\n\n")

    assert "drunk on pleasure" not in blocks[2]
    assert "drunk on pleasure" in blocks[4]
    assert "alfonso azpiri style" in blocks[1].lower()
    assert "lewd" in blocks[1].lower()


def test_anima_sanitizer_removes_photo_terms():
    from egodary.models_adapters.anima import AnimaAdapter

    adapter = AnimaAdapter()
    text = adapter._sanitize_block("photo realistic portrait, bokeh, depth of field, anime")
    assert "photo" not in text.lower()
    assert "bokeh" not in text.lower()
    assert "depth of field" not in text.lower()


def test_zimage_turbo_narrative_format():
    engine = create_engine()
    state = PromptState(
        model_id="zimage_turbo",
        scene=SceneState(time="sunset", weather="clear_sky"),
        camera=CameraState(angle="low_angle"),
    )
    result = engine.assemble(state)
    text = result.positive.lower()
    assert result.negative is None
    assert "keep style coherent" in text
    assert "." in result.positive
    assert "1girl" not in text
    assert "solo" not in text
    assert "a young woman" in text


def test_phase6_location_conflict_clears_weather_for_space():
    engine = create_engine()
    state = PromptState(
        model_id="illustrious",
        scene=SceneState(location="space_station", weather="rain", season="winter"),
    )
    result = engine.assemble(state)
    assert "rain" not in result.positive.lower()
    assert "winter" not in result.positive.lower()


def test_scene_location_and_environment_location_are_alternatives_not_both():
    """Regression test: scene.location is a legacy field with no UI control
    left in the app (superseded by environment.location's Indoor / Outdoor &
    Semi-Outdoor / Fantasy & Stylized tree) — a leftover value from an old
    session must not get concatenated onto whatever the user actually picks
    in the current environment.location tree."""
    from egodary.core.models import EnvironmentState

    engine = create_engine()

    # Both set: environment.location (the current UI) must win outright,
    # the legacy scene.location value must not appear at all.
    state_both = PromptState(
        model_id="anima",
        scene=SceneState(location="luxury_apartment"),
        environment=EnvironmentState(location="penthouse"),
    )
    result_both = engine.assemble(state_both)
    text_both = result_both.positive.lower()
    assert "penthouse" in text_both
    assert "luxury apartment with floor-to-ceiling windows" not in text_both

    # Only the legacy field set: it must still work as a fallback (old
    # sessions that never touched environment.location shouldn't lose their
    # location entirely).
    state_legacy_only = PromptState(
        model_id="anima",
        scene=SceneState(location="luxury_apartment"),
    )
    result_legacy_only = engine.assemble(state_legacy_only)
    assert "luxury apartment with floor-to-ceiling windows" in result_legacy_only.positive.lower()


def test_fetish_exclusive_gag_conflict():
    from egodary.core.conflicts import apply_state_conflicts
    from egodary.core.models import FetishState, PromptState

    state = PromptState(
        fetish=FetishState(elements=["ball_gag", "bit_gag", "blindfold"]),
    )
    resolved, warnings = apply_state_conflicts(state)
    gags = [item for item in resolved.fetish.elements if item in ("ball_gag", "bit_gag")]
    assert len(gags) == 1
    assert "blindfold" in resolved.fetish.elements
    assert warnings


def test_fetish_elements_in_prompt():
    from egodary.core.models import FetishState

    engine = create_engine()
    state = PromptState(
        model_id="illustrious",
        fetish=FetishState(elements=["rope_bondage_shibari", "riding_crop"]),
    )
    result = engine.assemble(state)
    text = result.positive.lower()
    assert "shibari" in text or "rope bondage" in text
    assert "riding crop" in text


def test_phase9_import_and_convert_helpers():
    from egodary.bootstrap import build_app

    registry, _ = build_app()
    result = import_prompt_with_report(
        "sunset, clear sky, low angle, 85mm lens, neon backpack",
        "illustrious",
        registry,
    )
    assert result.state.scene.time == "sunset"
    assert result.state.scene.weather == "clear_sky"
    assert result.state.camera.angle == "low_angle"
    assert result.state.camera.lens == "85mm_portrait"
    assert any(m.item_id == "neon_backpack" for m in result.matched)
    assert len(result.matched) > 0
    converted = convert_prompt("sunset, clear sky, 1girl", "illustrious", "zimage_turbo")
    assert "Keep style coherent" in converted


def test_import_records_unknown_tokens():
    from egodary.bootstrap import build_app
    from egodary.core.importer import import_prompt_with_report
    from egodary.persistence.db import init_db
    from egodary.persistence.schema import list_unknown_tags, record_unknown_tags

    registry, _ = build_app()
    init_db()
    result = import_prompt_with_report(
        "sunset, qqqzzzyyy_unknown_xyz, clear sky",
        "illustrious",
        registry,
    )
    assert any("qqqzzzyyy" in u.lower() for u in result.unknown)
    record_unknown_tags(result.unknown, "test prompt")
    rows = list_unknown_tags(limit=10)
    assert any("qqqzzzyyy" in row["token"].lower() for row in rows)


def test_duplicate_category_raises():
    registry = TagRegistry()
    category = TagCategory(id="cat.a", title="A", items=[TagItem(id="x", label="X", tags={"illustrious": "tag"})])
    registry.register_category(category, source_plugin="pack_a")
    with pytest.raises(RegistryConflictError):
        registry.register_category(category, source_plugin="pack_b")
