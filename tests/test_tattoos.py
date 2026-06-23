from egodary.app import create_engine
from egodary.core.models import AppearanceState, OutfitState, PromptState
from egodary.core.tattoos import sort_tattoo_ids


def test_tattoos_bucket_order_and_prompt():
    engine = create_engine()
    state = PromptState(
        outfit=OutfitState(dress="bodycon_micro_dress"),
        appearance=AppearanceState(
            tattoos=[
                "rose_tattoo",
                "realistic_tattoo",
                "thigh_tattoo",
            ],
        ),
    )
    sorted_ids = sort_tattoo_ids(engine.registry, state.appearance.tattoos)
    assert sorted_ids.index("realistic_tattoo") < sorted_ids.index("thigh_tattoo")
    assert sorted_ids.index("thigh_tattoo") < sorted_ids.index("rose_tattoo")

    result = engine.assemble(state)
    parts = [p.strip() for p in result.positive.split(",")]
    dress_idx = next(i for i, p in enumerate(parts) if "bodycon micro dress" in p.lower())
    style_idx = next(i for i, p in enumerate(parts) if p.lower() == "realistic tattoo")
    placement_idx = next(i for i, p in enumerate(parts) if p.lower() == "thigh tattoo")
    theme_idx = next(i for i, p in enumerate(parts) if p.lower() == "rose tattoo")
    assert dress_idx < style_idx < placement_idx < theme_idx


def test_tattoos_separate_from_accessories_bucket():
    engine = create_engine()
    state = PromptState(
        appearance=AppearanceState(
            accessories=["o_ring_choker"],
            tattoos=["japanese_tattoo", "sleeve_tattoo"],
        ),
    )
    result = engine.assemble(state)
    positive = result.positive.lower()
    assert "japanese tattoo" in positive
    assert "sleeve tattoo" in positive
    assert "o-ring choker" in positive or "o_ring_choker" in positive or "choker" in positive
