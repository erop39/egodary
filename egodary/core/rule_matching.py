"""Shared rule matching for conflict warnings and quality scoring."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from egodary.core.models import PromptState

CONTENT_DIR = Path(__file__).resolve().parents[1] / "content"

STATE_FIELD_ALIASES: dict[str, tuple[str, str]] = {
    "camera_angle": ("camera", "angle"),
    "camera_framing": ("camera", "framing"),
    "camera_lens": ("camera", "lens"),
    "camera_focus": ("camera", "focus"),
    "camera_composition": ("camera", "composition"),
    "camera_nsfw_shot": ("camera", "nsfw_shot"),
    "lighting_light_type": ("lighting", "light_type"),
    "lighting_direction": ("lighting", "direction"),
    "lighting_quality": ("lighting", "quality"),
    "lighting_color_mood": ("lighting", "color_mood"),
    "lighting_nsfw": ("lighting", "nsfw"),
    "face_facial_expression": ("face", "facial_expression"),
    "face_mouth_lips": ("face", "mouth_lips"),
    "face_eyes": ("face", "eyes"),
    "face_beauty_archetype": ("face", "beauty_archetype"),
    "scene_location": ("scene", "location"),
    "scene_weather": ("scene", "weather"),
    "scene_season": ("scene", "season"),
    "scene_time": ("scene", "time"),
    "environment_location": ("environment", "location"),
    "pose": ("", "pose"),
    "character_breast_size": ("character", "breast_size"),
    "character_breast_shape": ("character", "breast_shape"),
    "character_body_type": ("character", "body_type"),
    "character_waist": ("character", "waist"),
    "character_hips_ass": ("character", "hips_ass"),
    "character_legs": ("character", "legs"),
    "character_overall_figure": ("character", "overall_figure"),
    "character_height_build": ("character", "height_build"),
}

PACK_FIELD_SUFFIX = "_ids"
SEVERITY_PREFIX = {
    "hard_block": "[Hard]",
    "strong_warning": "[Strong]",
    "soft_warning": "[Hint]",
    "overload": "[Strong]",
}


@lru_cache(maxsize=1)
def _legacy_location_environment_groups() -> dict[str, str]:
    path = CONTENT_DIR / "scene_location_pack" / "location_groups.yaml"
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    mapping: dict[str, str] = {}
    for group, ids in (data.get("groups") or {}).items():
        for loc_id in ids:
            mapping[loc_id] = group
    return mapping


@lru_cache(maxsize=1)
def _environment_rules() -> dict[str, Any]:
    path = CONTENT_DIR / "environment_pack" / "environment_rules.yaml"
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=1)
def _scene_environment_types() -> dict[str, dict[str, bool]]:
    from egodary.core.conflicts import SCENE_CONFLICTS

    return dict(SCENE_CONFLICTS)


def _get_nested_value(state: PromptState, obj_name: str, field: str) -> str:
    if obj_name:
        return getattr(getattr(state, obj_name), field) or ""
    return getattr(state, field) or ""


def _character_scalar_ids(state: PromptState) -> set[str]:
    ch = state.character
    values = (
        ch.age_appearance,
        ch.body_type,
        ch.breast_size,
        ch.breast_shape,
        ch.waist,
        ch.hips_ass,
        ch.legs,
        ch.overall_figure,
        ch.height_build,
        ch.ethnicity,
        ch.skin_tone,
    )
    return {value for value in values if value}


def _character_active_ids(state: PromptState) -> set[str]:
    return _character_scalar_ids(state) | set(state.character.body_details)


def _fetish_active_ids(state: PromptState) -> set[str]:
    return set(state.fetish.elements)


def _fetish_active_count(state: PromptState) -> int:
    return len(state.fetish.elements)


def _camera_values(state: PromptState) -> set[str]:
    cam = state.camera
    return {
        value
        for value in (
            cam.angle,
            cam.framing,
            cam.lens,
            cam.focus,
            cam.composition,
            cam.nsfw_shot,
        )
        if value
    }


def _lighting_filled_count(state: PromptState) -> int:
    light = state.lighting
    return sum(
        1
        for field in ("light_type", "direction", "quality", "color_mood", "nsfw")
        if getattr(light, field)
    )


def _environment_location_group(location_id: str) -> str:
    if not location_id:
        return ""
    groups = (_environment_rules().get("location_groups") or {})
    for group, ids in groups.items():
        if location_id in ids:
            return group
    if location_id in _scene_environment_types():
        return location_id
    return _legacy_location_environment_groups().get(location_id, "")


def _resolve_state_value(state: PromptState, key: str) -> Any:
    if key == "pose_empty":
        return not state.pose
    if key == "fetish_count_min":
        return _fetish_active_count(state)
    if key == "fetish_count_max":
        return _fetish_active_count(state)
    if key == "fetish_count_gt":
        return _fetish_active_count(state)
    if key == "lighting_fields_gt":
        return _lighting_filled_count(state)
    if key == "scene_weather_set":
        return bool(state.scene.weather)
    if key == "scene_season_set":
        return bool(state.scene.season)
    if key in STATE_FIELD_ALIASES:
        obj_name, field = STATE_FIELD_ALIASES[key]
        return _get_nested_value(state, obj_name, field)
    if key == "scene_location_group":
        location = state.scene.location or state.environment.location
        if location in _scene_environment_types():
            return location
        group = _environment_location_group(location)
        if group:
            return group
        return _legacy_location_environment_groups().get(location, "")
    if key == "environment_location_in_group":
        return _environment_location_group(state.environment.location)
    return None


def _match_scalar(actual: Any, expected: Any) -> bool:
    if isinstance(expected, bool):
        return bool(actual) is expected
    if isinstance(expected, int) and not isinstance(expected, bool):
        return actual == expected
    if isinstance(expected, list):
        return actual in expected
    return actual == expected


def _match_when_clause(state: PromptState, when: dict[str, Any]) -> bool:
    for key, expected in when.items():
        if key == "fetish_active":
            active = _fetish_active_ids(state)
            ids = set(expected or ())
            if not ids.intersection(active):
                return False
            continue
        if key == "character_any":
            active = _character_active_ids(state)
            ids = set(expected or ())
            if not ids.intersection(active):
                return False
            continue
        if key == "character_all":
            active = _character_active_ids(state)
            ids = set(expected or ())
            if not ids.issubset(active):
                return False
            continue
        if key == "fetish_any":
            active = _fetish_active_ids(state)
            ids = set(expected or ())
            if not ids.intersection(active):
                return False
            continue
        if key == "fetish_all":
            active = _fetish_active_ids(state)
            ids = set(expected or ())
            if not ids.issubset(active):
                return False
            continue
        if key == "fetish_count_min":
            if _fetish_active_count(state) < int(expected):
                return False
            continue
        if key == "fetish_count_max":
            if _fetish_active_count(state) > int(expected):
                return False
            continue
        if key == "fetish_count_gt":
            if _fetish_active_count(state) <= int(expected):
                return False
            continue
        if key == "lighting_fields_gt":
            if _lighting_filled_count(state) <= int(expected):
                return False
            continue
        if key == "camera_all_groups":
            values = _camera_values(state)
            for group in expected or ():
                group_ids = set(group or ())
                if not values.intersection(group_ids):
                    return False
            continue
        if key == "environment_location_in_group":
            loc = state.environment.location
            groups = _environment_rules().get("location_groups") or {}
            group_ids = set(groups.get(expected, []) or ())
            if loc not in group_ids:
                return False
            continue
        if key == "environment_modifiers_any":
            active = set(state.environment.modifiers)
            if not active.intersection(set(expected or ())):
                return False
            continue
        if key == "scene_location_group":
            actual = _resolve_state_value(state, key)
            if not _match_scalar(actual, expected):
                return False
            continue

        actual = _resolve_state_value(state, key)
        if actual is None and key in STATE_FIELD_ALIASES:
            obj_name, field = STATE_FIELD_ALIASES[key]
            actual = _get_nested_value(state, obj_name, field)
        if not _match_scalar(actual, expected):
            return False
    return True


def match_when(state: PromptState, when: dict[str, Any] | None) -> bool:
    """Return True when every condition in *when* matches *state*."""
    if not when:
        return False
    if "any" in when:
        branches = when.get("any") or []
        return any(match_when(state, branch) for branch in branches)
    return _match_when_clause(state, when)


def match_pack_compatibility_rule(state: PromptState, rule: dict[str, Any], domain: str) -> bool:
    """Match legacy pack ``compatibility_warnings`` rules (camera/lighting)."""
    if rule.get("requires_static_pose"):
        angle_ids = set(rule.get("angle_ids") or ())
        return state.camera.angle in angle_ids and not state.pose

    obj = getattr(state, domain)
    active_fields = [
        field
        for field in (
            "angle",
            "framing",
            "lens",
            "focus",
            "composition",
            "nsfw_shot",
            "light_type",
            "direction",
            "quality",
            "color_mood",
            "nsfw",
        )
        if rule.get(f"{field}{PACK_FIELD_SUFFIX}")
    ]
    if not active_fields:
        return False

    for field in active_fields:
        value = getattr(obj, field, "")
        allowed = set(rule.get(f"{field}{PACK_FIELD_SUFFIX}") or ())
        if not value or value not in allowed:
            return False
    return True


@lru_cache(maxsize=1)
def load_cross_rules() -> dict[str, Any]:
    from egodary.core.rules_loader import get_general_rules

    bundle = get_general_rules()
    return {
        "meta": bundle.meta,
        "penalties": bundle.penalties,
        "bonuses": bundle.bonuses,
        "scoring": bundle.scoring,
        "policies": bundle.policies,
    }


def format_rule_message(rule: dict[str, Any], *, bonus: bool = False) -> str:
    message = rule.get("message", "")
    if bonus:
        return f"[Hint] {message}" if not message.startswith("[") else message
    severity = rule.get("severity", "strong_warning")
    prefix = SEVERITY_PREFIX.get(severity, "[Strong]")
    if message.startswith("["):
        return message
    return f"{prefix} {message}"


def iter_cross_penalties(state: PromptState, *, emit_warning: bool | None = None) -> list[dict[str, Any]]:
    rules = load_cross_rules().get("penalties") or []
    matched: list[dict[str, Any]] = []
    for rule in rules:
        if emit_warning is not None and bool(rule.get("emit_warning")) != emit_warning:
            continue
        if match_when(state, rule.get("when") or {}):
            matched.append(rule)
    return matched


def iter_cross_bonuses(state: PromptState) -> list[dict[str, Any]]:
    rules = load_cross_rules().get("bonuses") or []
    return [rule for rule in rules if match_when(state, rule.get("when") or {})]


def iter_pack_compatibility_warnings(state: PromptState, rules: dict[str, Any], domain: str) -> list[str]:
    messages: list[str] = []
    for rule in rules.get("compatibility_warnings") or []:
        if match_pack_compatibility_rule(state, rule, domain):
            messages.append(rule["message"])
    return messages
