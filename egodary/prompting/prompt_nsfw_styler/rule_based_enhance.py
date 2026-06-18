"""Deterministic NSFW enhancement using registry NSFW categories."""

from __future__ import annotations

import copy
import random

from egodary.core.models import PromptState
from egodary.core.runtime_registry import RuntimeRegistry
from egodary.prompting.prompt_analyze.extract_core import CorePrompt
from egodary.prompting.prompt_nsfw_styler.intensity import NsfwIntensity, intensity_to_lewdness

_INTENSITY_PICKS: dict[NsfwIntensity, dict[str, list[tuple[str, str]]]] = {
    "low": {
        "camera.nsfw_shot": [("looking_up_from_below", "camera.nsfw_shot")],
        "lighting.nsfw": [("soft_glowing_skin_lighting", "lighting.nsfw")],
        "outfit.dress": [("lace_sheer_dress", "outfit.dress")],
    },
    "medium": {
        "camera.nsfw_shot": [("high_angle_submission_shot", "camera.nsfw_shot")],
        "lighting.nsfw": [("moody_bedroom_lighting", "lighting.nsfw")],
        "pose.solo": [("leaning_against_wall_one_leg_up", "pose")],
        "fetish.elements": [],
    },
    "high": {
        "camera.nsfw_shot": [("low_angle_dominance_shot", "camera.nsfw_shot")],
        "outfit.dress": [("micro_mini_dress", "outfit.dress")],
        "pose.solo": [("on_all_fours_ass_high_chest_low", "pose")],
        "lighting.nsfw": [("side_lighting_emphasizing_breasts", "lighting.nsfw")],
    },
    "extreme": {
        "camera.nsfw_shot": [("extreme_close_up_on_lips", "camera.nsfw_shot")],
        "outfit.dress": [("sheer_micro_dress", "outfit.dress")],
        "pose.solo": [("on_all_fours_with_extreme_arch", "pose")],
        "lighting.nsfw": [("dramatic_lighting_on_ass", "lighting.nsfw")],
        "fetish.elements": [],
    },
}


def _first_item_id(registry: RuntimeRegistry, category_id: str, *, min_level: int = 0) -> str | None:
    category = registry.get_category(category_id)
    if not category:
        return None
    for item in category.items:
        if item.id == "none":
            continue
        if item.min_level is not None and item.min_level > min_level:
            continue
        return item.id
    return None


def _is_locked(field_path: str, core: CorePrompt | None) -> bool:
    if core is None:
        return False
    return field_path in core.locked_paths or any(
        field_path.startswith(p.rstrip(".")) for p in core.locked_paths
    )


def _get_field(state: PromptState, field_path: str) -> str | list[str]:
    if field_path == "pose":
        return state.pose
    section, fld = field_path.split(".", 1)
    container = getattr(state, section)
    return getattr(container, fld)


def _set_field(state: PromptState, field_path: str, value: str) -> None:
    if field_path == "pose":
        state.pose = value
        return
    section, fld = field_path.split(".", 1)
    container = getattr(state, section)
    current = getattr(container, fld)
    if isinstance(current, list):
        if value not in current:
            current.append(value)
    else:
        setattr(container, fld, value)


def rule_based_enhance(
    state: PromptState,
    intensity: NsfwIntensity,
    registry: RuntimeRegistry,
    core: CorePrompt | None = None,
    *,
    force: bool = False,
) -> PromptState:
    """Enhance NSFW-related fields without mutating locked core paths."""
    out = copy.deepcopy(state)
    out.lewdness = intensity_to_lewdness(intensity)
    picks = _INTENSITY_PICKS.get(intensity, {})
    min_level_map = {"low": 3, "medium": 5, "high": 8, "extreme": 10}

    for category_id, candidates in picks.items():
        for preferred_id, field_path in candidates:
            if _is_locked(field_path, core):
                continue
            current = _get_field(out, field_path)
            if not force and ((isinstance(current, str) and current) or (isinstance(current, list) and current)):
                continue
            item_id = preferred_id if registry.resolve_tag(category_id, preferred_id, out.model_id) else None
            if not item_id:
                item_id = _first_item_id(registry, category_id, min_level=min_level_map[intensity])
            if item_id:
                _set_field(out, field_path, item_id)

    if intensity in ("medium", "high", "extreme"):
        fetish_cat = registry.get_category("fetish.elements")
        if fetish_cat and (force or not out.fetish.elements):
            pool = [
                item.id
                for item in fetish_cat.items
                if item.id != "none" and (item.min_level is None or item.min_level <= min_level_map[intensity])
            ]
            if pool and (force or not out.fetish.elements):
                pick = random.choice(pool[: min(3, len(pool))])
                if pick not in out.fetish.elements:
                    out.fetish.elements.append(pick)

    return out
