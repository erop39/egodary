from egodary.core.clothing_state_bind import bind_clothing_modifiers_to_garment


def test_bind_single_modifier_illustrious():
    result = bind_clothing_modifiers_to_garment(
        "bodycon micro dress",
        ["pulled down"],
        model_id="illustrious",
    )
    assert result == "pulled down bodycon micro dress"


def test_bind_multiple_modifiers_illustrious():
    result = bind_clothing_modifiers_to_garment(
        "bodycon micro dress",
        ["pulled down", "wet soaked"],
        model_id="illustrious",
    )
    assert result == "pulled down wet soaked bodycon micro dress"


def test_bind_anima_keeps_styled_outfit_and_detail():
    result = bind_clothing_modifiers_to_garment(
        "bodycon micro dress, styled outfit",
        ["pulled down", "clothing detail"],
        model_id="anima",
    )
    assert result == "pulled down bodycon micro dress, styled outfit, clothing detail"


def test_bind_dress_pulled_down_example():
    from egodary.app import create_engine
    from egodary.core.models import OutfitState, PromptState

    engine = create_engine()
    state = PromptState(
        outfit=OutfitState(
            dress="bodycon_micro_dress",
            conditions={"dress": {"partial_removal": "pulled_down", "moisture": "wet_soaked"}},
        )
    )
    result = engine.assemble(state)
    positive = result.positive.lower()
    assert "pulled down wet soaked bodycon micro dress" in positive

    result = bind_clothing_modifiers_to_garment(
        "wearing bodycon micro dress",
        ["wearing pulled down", "wearing wet soaked"],
        model_id="zimage_turbo",
    )
    assert result == "wearing pulled down wet soaked bodycon micro dress"
