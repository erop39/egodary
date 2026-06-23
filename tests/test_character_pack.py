"""Tests for character_pack catalog."""

from egodary.bootstrap import build_app


def test_character_pack_has_catalog_categories():
    registry, _ = build_app()
    checks = {
        "character.age_appearance": 8,
        "character.body_type": 12,
        "character.breast_size": 5,
        "character.breast_shape": 8,
        "character.legs": 12,
        "character.body_details": 31,
        "character.ethnicity": 12,
        "character.skin_tone": 8,
    }
    for cat_id, min_items in checks.items():
        category = registry.get_category(cat_id)
        assert category is not None
        assert len(category.items) >= min_items


def test_character_body_tags_in_prompt():
    from egodary.app import create_engine
    from egodary.core.models import CharacterState, PromptState

    engine = create_engine()
    state = PromptState(
        model_id="illustrious",
        character=CharacterState(
            age_appearance="21_25",
            body_type="curvy",
            breast_size="large_breasts",
            ethnicity="latina",
        ),
    )
    result = engine.assemble(state)
    text = result.positive.lower()
    assert "curvy" in text
    assert "large breasts" in text
    assert "latina" in text


def test_character_dedupes_duplicate_thick_thighs_tag():
    from egodary.app import create_engine
    from egodary.core.models import CharacterState, PromptState

    engine = create_engine()
    state = PromptState(
        model_id="illustrious",
        character=CharacterState(
            hips_ass="thick_thighs",
            legs="thick_thighs",
        ),
    )
    result = engine.assemble(state)
    assert result.positive.lower().count("thick thighs") == 1
