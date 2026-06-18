from egodary.core.models import TagItem
from egodary.core.tag_deduplication import TagDeduplicationService


def test_tag_deduplication_exact_name():
    service = TagDeduplicationService()
    items = [
        TagItem(
            id="one",
            label="Neon Dress",
            tags={"illustrious": "neon dress"},
            meta={"subcategory_id": "imported", "subgroup": "imported"},
        )
    ]
    matches = service.find_matches(phrase="neon dress", category_id="outfit.dress", items=items)
    assert matches
    assert matches[0].match_type == "exact_name"


def test_tag_deduplication_alias_collision():
    service = TagDeduplicationService()
    items = [
        TagItem(
            id="one",
            label="Neon Dress",
            tags={"illustrious": "neon dress"},
            meta={
                "subcategory_id": "imported",
                "subgroup": "imported",
                "aliases": ["uv outfit", "club_dress"],
            },
        )
    ]
    matches = service.find_matches(phrase="uv outfit", category_id="outfit.dress", items=items)
    assert matches
    assert matches[0].match_type == "alias_collision"


def test_tag_deduplication_fuzzy_name():
    service = TagDeduplicationService(fuzzy_threshold=0.8)
    items = [
        TagItem(
            id="one",
            label="neon latex corset",
            tags={"illustrious": "neon latex corset"},
            meta={"subcategory_id": "imported", "subgroup": "imported"},
        )
    ]
    matches = service.find_matches(phrase="neon latex corsett", category_id="outfit.top", items=items)
    assert matches
    assert matches[0].match_type == "fuzzy_name"
