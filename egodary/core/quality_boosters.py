"""Score-tag quality boosters for prompt assembly (primarily Anima)."""

from __future__ import annotations

from egodary.core.models import StyleState

QUALITY_BOOSTER_LEVELS = ("low", "medium", "high")

QUALITY_BOOSTER_MODEL_IDS = frozenset({"anima"})

QUALITY_BOOSTER_TAGS: dict[str, list[str]] = {
    "low": ["score_7_up"],
    "medium": ["score_8_up", "score_7_up"],
    "high": ["score_9", "score_8_up", "score_7_up"],
}

def is_score_rating_tag(tag: str) -> bool:
    """Danbooru-style score_* tags used by Anima boosters, not Illustrious."""
    normalized = tag.strip().lower().replace(" ", "_")
    return normalized.startswith("score_")


def resolve_quality_booster_tags(style: StyleState, model_id: str) -> list[str]:
    """Return score tags to prepend when boosters are enabled (Anima only)."""
    if model_id not in QUALITY_BOOSTER_MODEL_IDS:
        return []
    if not style.quality_boosters_enabled:
        return []
    level = (style.quality_boosters_level or "high").strip().lower()
    if level not in QUALITY_BOOSTER_TAGS:
        level = "high"
    return list(QUALITY_BOOSTER_TAGS[level])


def finalize_quality_bucket(tags: list[str], style: StyleState, model_id: str) -> list[str]:
    """Apply boosters for Anima and strip score_* tags from other models."""
    if model_id in QUALITY_BOOSTER_MODEL_IDS:
        booster_tags = resolve_quality_booster_tags(style, model_id)
        if booster_tags:
            existing = {tag.lower() for tag in tags}
            prefix = [tag for tag in booster_tags if tag.lower() not in existing]
            tags = prefix + tags
        return tags
    return [tag for tag in tags if not is_score_rating_tag(tag)]
