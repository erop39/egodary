"""Prompt quality and consistency scoring."""

from __future__ import annotations

from egodary.core.models import PromptBuckets, PromptState

PROMPT_RULEBOOK_MIN_SCORE = 6


def calculate_prompt_quality_score(buckets: PromptBuckets) -> int:
    score = 0
    if buckets.face:
        score += 5
    if buckets.subject:
        score += 1
    if buckets.character:
        score += 2
    if buckets.appearance:
        score += 1
    if buckets.scene:
        score += 2
    if buckets.camera:
        score += 1
    if buckets.outfit:
        score += 1
    if buckets.lighting:
        score += 1
    if buckets.quality:
        score += 1
    if buckets.atmosphere:
        score += 1
    return min(score, 10)


def calculate_character_consistency_score(state: PromptState) -> int:
    char = state.character
    score = 4
    if char.body_type:
        score += 1
    if char.breast_size or char.overall_figure:
        score += 1
    if char.ethnicity or char.skin_tone:
        score += 1
    if state.characters.secondary:
        score += 1
        if state.characters.auto_contrast:
            score += 1
    return min(score, 10)


def resolve_color_harmony(tags: list[str]) -> int:
    text = " ".join(tags).lower()
    if "golden" in text and "blue hour" in text:
        return 6
    if "warm" in text and "cool" in text:
        return 7
    return 8

