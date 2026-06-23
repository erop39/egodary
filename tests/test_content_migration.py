"""Tests for migrated eGen content packs."""

from egodary.bootstrap import build_app


def test_scene_location_pack_full_environment_groups():
    registry, _ = build_app()
    category = registry.get_category("scene.location")
    assert category is not None
    assert len(category.items) == 80
    groups = {item.meta.get("environment_group") for item in category.items}
    assert groups == {"indoor", "outdoor", "fantasy", "cyberpunk", "space", "transport"}


def test_outfit_pack_has_extended_categories():
    registry, _ = build_app()
    checks = {
        "outfit.dress": 50,
        "outfit.top": 40,
        "outfit.bottom": 80,
        "outfit.legwear": 20,
        "outfit.jacket": 30,
        "outfit.footwear": 32,
        "outfit.gloves": 26,
        "outfit.cape": 28,
    }
    for cat_id, min_items in checks.items():
        category = registry.get_category(cat_id)
        assert category is not None
        assert len(category.items) >= min_items


def test_fetish_pack_has_elements_catalog():
    registry, _ = build_app()
    category = registry.get_category("fetish.elements")
    assert category is not None
    assert len(category.items) == 58
    subgroups = {item.meta.get("subgroup") for item in category.items}
    assert subgroups == {
        "bdsm_restraints",
        "toys_accessories",
        "body_marks",
        "fluids_wetness",
        "body_writing",
        "specific_details",
        "advanced_heavy",
    }


def test_fetish_external_skip_latex_catsuit():
    from egodary.core.fetish_skip import should_skip_fetish_item
    from egodary.core.models import FetishState, OutfitState, PromptState

    state = PromptState(
        outfit=OutfitState(dress="black_latex_long_dress"),
        fetish=FetishState(elements=["latex_catsuit_if_not_in_outfit"]),
    )
    assert should_skip_fetish_item(state, "latex_catsuit_if_not_in_outfit")


def test_outfit_dress_clears_bottom_and_top():
    from egodary.core.conflicts import apply_state_conflicts
    from egodary.core.models import OutfitState, PromptState

    state = PromptState(
        outfit=OutfitState(
            dress="black_latex_long_dress",
            top="black_harness_top",
            bottom="micro_mini_skirt",
            legwear="sheer_pantyhose",
        )
    )
    resolved, warnings = apply_state_conflicts(state)
    assert resolved.outfit.top == ""
    assert resolved.outfit.bottom == ""
    assert resolved.outfit.legwear == ""
    assert resolved.outfit.dress == "black_latex_long_dress"
    assert any("Dress" in w for w in warnings)


def test_outfit_nsfw_dress_layering_allowed():
    from egodary.core.conflicts import apply_state_conflicts
    from egodary.core.models import OutfitState, PromptState

    state = PromptState(
        outfit=OutfitState(
            dress="sheer_micro_dress",
            top="black_harness_top",
            bottom="micro_mini_skirt",
            legwear="sheer_thigh_high_stockings",
        )
    )
    resolved, _ = apply_state_conflicts(state)
    assert resolved.outfit.dress == "sheer_micro_dress"
    assert resolved.outfit.top == "black_harness_top"
    assert resolved.outfit.bottom == ""
    assert resolved.outfit.legwear == "sheer_thigh_high_stockings"


def test_outfit_legwear_blocked_with_long_pants():
    from egodary.core.conflicts import apply_state_conflicts
    from egodary.core.models import OutfitState, PromptState

    state = PromptState(outfit=OutfitState(bottom="skinny_jeans", legwear="sheer_pantyhose"))
    resolved, _ = apply_state_conflicts(state)
    assert resolved.outfit.legwear == ""


def test_outfit_nsfw_underwear_with_legwear_allowed():
    """Underwear (в bottom) + legwear должны сосуществовать без конфликтов."""
    from egodary.core.conflicts import apply_state_conflicts
    from egodary.core.models import OutfitState, PromptState

    state = PromptState(
        outfit=OutfitState(
            bottom="extreme_micro_thong",
            legwear="sheer_thigh_high_stockings",
        )
    )
    resolved, warnings = apply_state_conflicts(state)
    assert resolved.outfit.bottom == "extreme_micro_thong"
    assert resolved.outfit.legwear == "sheer_thigh_high_stockings"


def test_outfit_underwear_conditions_use_separate_key_from_bottom():
    """Underwear conditions хранятся под ключом "underwear", не "bottom",
    чтобы не конфликтовать с pants/skirt conditions в том же слоте."""
    from egodary.app import get_engine
    from egodary.core.models import OutfitState, PromptState

    engine = get_engine()
    state = PromptState(
        outfit=OutfitState(
            bottom="extreme_micro_thong",
            conditions={"underwear": {"moisture": "wet_soaked"}},
        )
    )
    result = engine.assemble(state)
    outfit_tags = " ".join(result.buckets.outfit)
    assert "extreme micro thong" in outfit_tags
    assert "wet" in outfit_tags.lower()


def test_outfit_underwear_conditions_cleared_when_subgroup_changes():
    """Underwear conditions сбрасываются при переключении bottom subgroup
    на long_pants/skirts/shorts (synced by backend)."""
    from egodary.core.conflicts import apply_state_conflicts
    from egodary.core.models import OutfitState, PromptState

    state = PromptState(
        outfit=OutfitState(
            bottom="skinny_jeans",  # long_pants subgroup
            conditions={"underwear": {"moisture": "wet_soaked"}},
        )
    )
    resolved, _ = apply_state_conflicts(state)
    assert resolved.outfit.conditions.get("underwear", {}) == {}


def test_outfit_bottom_pants_conditions_independent_of_underwear():
    """Pants (long_pants subgroup) conditions хранятся под ключом "bottom",
    независимо от underwear conditions."""
    from egodary.app import get_engine
    from egodary.core.models import OutfitState, PromptState

    engine = get_engine()
    state = PromptState(
        outfit=OutfitState(
            bottom="skinny_jeans",
            conditions={"bottom": {"damage": "torn_ripped"}},
        )
    )
    result = engine.assemble(state)
    outfit_tags = " ".join(result.buckets.outfit)
    assert "skinny jeans" in outfit_tags
    assert "torn" in outfit_tags.lower()




def test_outfit_none_bottom_allows_legwear():
    """bottom=none не блокирует legwear."""
    from egodary.core.conflicts import apply_state_conflicts
    from egodary.core.models import OutfitState, PromptState

    state = PromptState(
        outfit=OutfitState(
            bottom="none",
            legwear="sheer_thigh_high_stockings",
        )
    )
    resolved, _ = apply_state_conflicts(state)
    assert resolved.outfit.bottom == "none"
    assert resolved.outfit.legwear == "sheer_thigh_high_stockings"


def test_outfit_dress_none_does_not_clear_other_layers():
    from egodary.core.conflicts import apply_state_conflicts
    from egodary.core.models import OutfitState, PromptState

    state = PromptState(
        outfit=OutfitState(dress="none", top="black_crop_top", bottom="micro_mini_skirt")
    )
    resolved, _ = apply_state_conflicts(state)
    assert resolved.outfit.dress == "none"
    assert resolved.outfit.top == "black_crop_top"
    assert resolved.outfit.bottom == "micro_mini_skirt"


def test_appearance_pack_has_catalog_categories():
    registry, _ = build_app()
    checks = {
        "appearance.hair": 26,
        "appearance.hair_color": 24,
        "appearance.makeup": 22,
        "appearance.accessories": 32,
        "appearance.tattoos": 56,
    }
    for cat_id, min_items in checks.items():
        category = registry.get_category(cat_id)
        assert category is not None
        assert len(category.items) >= min_items


def test_appearance_hat_removed_with_complex_hair():
    from egodary.core.conflicts import apply_state_conflicts
    from egodary.core.models import AppearanceState, PromptState

    state = PromptState(
        appearance=AppearanceState(
            hair="space_buns",
            accessories=["o_ring_choker", "beanie_wetlook", "latex_collar"],
        )
    )
    resolved, warnings = apply_state_conflicts(state)
    assert "beanie_wetlook" not in resolved.appearance.accessories
    assert "o_ring_choker" in resolved.appearance.accessories
    assert any("hat" in w.lower() or "hairstyle" in w.lower() for w in warnings)


def test_appearance_accessories_trimmed_to_max():
    from egodary.core.conflicts import apply_state_conflicts
    from egodary.core.models import AppearanceState, PromptState

    state = PromptState(
        appearance=AppearanceState(
            accessories=[
                "o_ring_choker",
                "latex_collar",
                "strappy_harness_choker",
                "wide_leather_choker",
                "chain_choker_with_pendant",
            ]
        )
    )
    resolved, _ = apply_state_conflicts(state)
    assert len(resolved.appearance.accessories) == 4


def test_pose_pack_has_solo_and_couple_categories():
    registry, _ = build_app()
    solo = registry.get_category("pose.solo")
    couple = registry.get_category("pose.couple")
    assert solo is not None
    assert couple is not None
    assert len(solo.items) == 90
    assert len(couple.items) == 64
    solo_ids = solo.item_ids()
    couple_ids = couple.item_ids()
    assert solo_ids.isdisjoint(couple_ids)


def test_pose_couple_blocked_without_group_mode():
    from egodary.core.conflicts import apply_state_conflicts
    from egodary.core.models import PromptState

    state = PromptState(pose="missionary_legs_spread_wide", group_mode=False)
    resolved, warnings = apply_state_conflicts(state)
    assert resolved.pose == ""
    assert any("group mode" in w.lower() for w in warnings)


def test_pose_couple_allowed_with_group_mode():
    from egodary.core.conflicts import apply_state_conflicts
    from egodary.core.models import PromptState

    state = PromptState(pose="missionary_legs_spread_wide", group_mode=True)
    resolved, _ = apply_state_conflicts(state)
    assert resolved.pose == "missionary_legs_spread_wide"


def test_face_pack_has_all_categories():
    registry, _ = build_app()
    checks = {
        "face.facial_expression": 55,
        "face.mouth_lips": 30,
        "face.eyes": 31,
        "face.eye_color": 25,
        "face.face_shape": 24,
        "face.eyebrows": 23,
        "face.nose": 21,
        "face.jaw_chin": 20,
        "face.age_maturity": 20,
        "face.beauty_archetype": 29,
        "face.facial_details": 13,
    }
    for cat_id, min_items in checks.items():
        category = registry.get_category(cat_id)
        assert category is not None
        assert len(category.items) >= min_items


def test_face_tags_in_prompt():
    from egodary.app import create_engine
    from egodary.core.models import FaceState, PromptState

    engine = create_engine()
    state = PromptState(
        face=FaceState(facial_expression="classic_ahegao_tongue_out_eyes_rolled_up"),
    )
    result = engine.assemble(state)
    assert "ahegao" in result.positive.lower()


def test_clothing_state_added_to_outfit_bucket():
    from egodary.app import create_engine
    from egodary.core.models import OutfitState, PromptState

    engine = create_engine()
    state = PromptState(
        outfit=OutfitState(
            legwear="classic_fishnet_tights",
            conditions={
                "legwear": {
                    "moisture": "wet_soaked",
                    "damage": "torn_ripped",
                    "transparency": "see_through",
                }
            },
        )
    )
    result = engine.assemble(state)
    positive = result.positive.lower()
    assert "torn ripped see-through wet soaked classic fishnet tights" in positive
    assert "wet soaked clothing" not in positive
    assert "clothing pulled down" not in positive


def test_clothing_color_condition_applied_closest_to_garment():
    """Color modifier sits right before the garment noun, after other states."""
    from egodary.app import create_engine
    from egodary.core.models import OutfitState, PromptState

    engine = create_engine()
    state = PromptState(
        outfit=OutfitState(
            bottom="extreme_micro_thong",
            conditions={"underwear": {"moisture": "wet_soaked", "color": "emerald_green"}},
        )
    )
    result = engine.assemble(state)
    outfit_tags = " ".join(result.buckets.outfit).lower()
    assert "wet soaked emerald green extreme micro thong" in outfit_tags


def test_clothing_color_condition_alone():
    from egodary.app import create_engine
    from egodary.core.models import OutfitState, PromptState

    engine = create_engine()
    state = PromptState(
        outfit=OutfitState(
            top="black_harness_top",
            conditions={"top": {"color": "hot_pink"}},
        )
    )
    result = engine.assemble(state)
    outfit_tags = " ".join(result.buckets.outfit).lower()
    assert "hot pink black harness top" in outfit_tags


def test_bottom_subgroups_have_independent_conditions():
    """skirts/shorts/transparent_plastic_skirts/underwear each use their own
    condition key, separate from "bottom" (long_pants) and from each other."""
    from egodary.app import create_engine
    from egodary.core.models import OutfitState, PromptState

    engine = create_engine()

    cases = [
        ("micro_hotpants", "shorts", "rust"),
        ("micro_mini_skirt", "skirts", "lavender"),
        ("extreme_micro_thong", "underwear", "emerald_green"),
        ("skinny_jeans", "bottom", "navy_blue"),
    ]
    for bottom_value, condition_key, color_id in cases:
        state = PromptState(
            outfit=OutfitState(
                bottom=bottom_value,
                conditions={condition_key: {"color": color_id}},
            )
        )
        result = engine.assemble(state)
        outfit_tags = " ".join(result.buckets.outfit).lower()
        assert color_id.replace("_", " ") in outfit_tags, (
            f"{condition_key} condition not applied for {bottom_value}"
        )


def test_bottom_subgroup_conditions_cleared_on_subgroup_switch():
    """Switching the active bottom subgroup clears condition keys for the
    other subgroups (no leaking between shorts/skirts/underwear/pants)."""
    from egodary.core.conflicts import apply_state_conflicts
    from egodary.core.models import OutfitState, PromptState

    state = PromptState(
        outfit=OutfitState(
            bottom="micro_mini_skirt",  # skirts subgroup
            conditions={
                "shorts": {"color": "rust"},
                "underwear": {"color": "ivory"},
                "bottom": {"damage": "torn_ripped"},
                "skirts": {"color": "lavender"},
            },
        )
    )
    resolved, _ = apply_state_conflicts(state)
    assert resolved.outfit.conditions.get("shorts", {}) == {}
    assert resolved.outfit.conditions.get("underwear", {}) == {}
    assert resolved.outfit.conditions.get("bottom", {}) == {}
    assert resolved.outfit.conditions.get("skirts", {}) == {"color": "lavender"}


def test_clothing_color_catalog_has_all_requested_colors():
    """All colors from the spec are present in the outfit.clothing_state catalog."""
    from egodary.app import get_engine

    engine = get_engine()
    category = engine.registry.get_category("outfit.clothing_state")
    assert category is not None
    color_labels = {
        item.label for item in category.items if item.meta.get("dimension") == "color"
    }
    expected = {
        # Classic
        "Black", "White", "Beige", "Grey", "Navy Blue", "Brown",
        "Red", "Pink", "Camel", "Burgundy",
        # Trending 2025-2026
        "Olive Green", "Sage Green", "Dusty Rose", "Blush Pink",
        "Chocolate Brown", "Lavender", "Terracotta", "Butter Yellow",
        "Powder Blue", "Emerald Green", "Rust", "Mocha",
        # Additional
        "Charcoal Grey", "Ivory", "Hot Pink", "Wine Red",
    }
    assert expected.issubset(color_labels)
    assert len(color_labels) == len(expected)


def test_conflicts_preview_endpoint_reports_outfit_conflict():
    from egodary.core.models import OutfitState, PromptState

    from egodary.api.main import preview_conflicts

    state = PromptState(
        outfit=OutfitState(
            bottom="skinny_jeans",
            legwear="sheer_pantyhose",
        )
    )
    result = preview_conflicts(state)
    assert result["warnings"]
    assert any("legwear" in w.lower() for w in result["warnings"])


def test_space_station_blocks_weather():
    from egodary.app import create_engine
    from egodary.core.models import PromptState, SceneState

    engine = create_engine()
    state = PromptState(
        scene=SceneState(location="space_station", weather="rain", season="winter"),
    )
    result = engine.assemble(state)
    assert "rain" not in result.positive.lower()
    assert "winter" not in result.positive.lower()


def test_camera_pack_has_all_categories():
    registry, _ = build_app()
    checks = {
        "camera.angle": 15,
        "camera.framing": 15,
        "camera.lens": 6,
        "camera.focus": 9,
        "camera.composition": 17,
        "camera.nsfw_shot": 18,
    }
    for cat_id, expected in checks.items():
        cat = registry.get_category(cat_id)
        assert cat is not None, cat_id
        assert len(cat.items) == expected, cat_id


def test_camera_24mm_closeup_warning():
    from egodary.core.conflicts import apply_state_conflicts
    from egodary.core.models import CameraState, PromptState

    state = PromptState(
        camera=CameraState(
            lens="24mm_wide_angle",
            framing="close_up",
        ),
    )
    _, warnings = apply_state_conflicts(state)
    assert any("24mm" in w for w in warnings)


def test_camera_lens_pose_auto_fix():
    from egodary.core.conflicts import apply_state_conflicts
    from egodary.core.models import CameraState, PromptState

    state = PromptState(
        pose="on_all_fours_ass_high_chest_low",
        camera=CameraState(lens="85mm_portrait"),
    )
    resolved, warnings = apply_state_conflicts(state)
    assert resolved.camera.lens == "35mm"
    assert warnings


def test_lighting_pack_has_all_categories():
    registry, _ = build_app()
    checks = {
        "lighting.light_type": 20,
        "lighting.direction": 15,
        "lighting.quality": 15,
        "lighting.color_mood": 18,
        "lighting.nsfw": 20,
    }
    for cat_id, expected in checks.items():
        cat = registry.get_category(cat_id)
        assert cat is not None, cat_id
        assert len(cat.items) == expected, cat_id


def test_lighting_neon_warm_color_warning():
    from egodary.core.conflicts import apply_state_conflicts
    from egodary.core.models import LightingState, PromptState

    state = PromptState(
        lighting=LightingState(
            light_type="neon_lighting",
            color_mood="cozy_warm_light",
        ),
    )
    _, warnings = apply_state_conflicts(state)
    assert any("neon" in w.lower() for w in warnings)


def test_lighting_bucket_in_prompt():
    from egodary.app import create_engine
    from egodary.core.models import LightingState, PromptState

    engine = create_engine()
    state = PromptState(
        lighting=LightingState(
            light_type="candlelight",
            direction="rim_lighting",
        ),
    )
    result = engine.assemble(state)
    text = result.positive.lower()
    assert "candlelight" in text or "rim" in text

