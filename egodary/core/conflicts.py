"""Conflict engines for scene/outfit/camera/fetish compatibility."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from egodary.core.models import PromptState

OUTFIT_NONE_ID = "none"


def _outfit_item_active(value: str | None) -> bool:
    return bool(value) and value != OUTFIT_NONE_ID

SCENE_CONFLICTS = {
    "indoor": {"weather_block": True, "season_block": True},
    "space": {"weather_block": True, "season_block": True},
    "cyberpunk": {"weather_block": False, "season_block": False},
    "transport": {"weather_block": False, "season_block": False},
}

PROP_THEME_COMPAT = {
    "max_themes": 2,
}


@lru_cache(maxsize=1)
def _outfit_rules() -> dict:
    path = Path(__file__).resolve().parents[1] / "content" / "outfit_pack" / "outfit_rules.yaml"
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=1)
def _bottom_subgroup_by_id() -> dict[str, str]:
    rules = _outfit_rules()
    mapping: dict[str, str] = {}
    for subgroup, ids in (rules.get("bottom_subgroups") or {}).items():
        for item_id in ids:
            mapping[item_id] = subgroup
    return mapping


@lru_cache(maxsize=1)
def _environment_rules() -> dict:
    path = Path(__file__).resolve().parents[1] / "content" / "environment_pack" / "environment_rules.yaml"
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=1)
def _location_environment_groups() -> dict[str, str]:
    mapping: dict[str, str] = {}
    env_rules = _environment_rules()
    for group, ids in (env_rules.get("location_groups") or {}).items():
        for loc_id in ids:
            mapping[loc_id] = group
    path = Path(__file__).resolve().parents[1] / "content" / "scene_location_pack" / "location_groups.yaml"
    if path.is_file():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for group, ids in (data.get("groups") or {}).items():
            for loc_id in ids:
                mapping.setdefault(loc_id, group)
    return mapping


def _location_environment_type(location_id: str) -> str | None:
    if location_id in SCENE_CONFLICTS:
        return location_id
    return _location_environment_groups().get(location_id)


def _set_state_path(state: PromptState, path: str, value) -> None:
    parts = path.split(".")
    if len(parts) != 2:
        return
    obj_name, field = parts
    obj = getattr(state, obj_name, None)
    if obj is None:
        return
    setattr(obj, field, value)


def apply_environment_conflicts(state: PromptState, warnings: list[str]) -> None:
    """Trim environment modifiers and block weather/season for indoor locations."""
    env = state.environment
    rules = _environment_rules()
    max_modifiers = int((rules.get("multi_select_fields") or {}).get("modifiers") or 2)

    if len(env.modifiers) > max_modifiers:
        env.modifiers = env.modifiers[:max_modifiers]
        warnings.append(f"Atmospheric modifiers trimmed to {max_modifiers}.")

    location_id = env.location or state.scene.location
    env_type = _location_environment_type(location_id)
    indoor_groups = set(rules.get("indoor_groups") or ("indoor",))
    location_group = _location_environment_groups().get(location_id, "")
    is_indoor = env_type == "indoor" or location_group in indoor_groups

    scene = state.scene
    if is_indoor:
        if scene.weather:
            scene.weather = ""
            warnings.append("Weather cleared due to indoor environment compatibility.")
        if scene.season:
            scene.season = ""
            warnings.append("Season cleared due to indoor environment compatibility.")
    elif env_type in SCENE_CONFLICTS:
        rule = SCENE_CONFLICTS[env_type]
        if rule.get("weather_block") and scene.weather:
            scene.weather = ""
            warnings.append("Weather cleared due to location compatibility.")
        if rule.get("season_block") and scene.season:
            scene.season = ""
            warnings.append("Season cleared due to location compatibility.")


def _clear_fields(outfit, fields: tuple[str, ...]) -> list[str]:
    cleared: list[str] = []
    for field in fields:
        if getattr(outfit, field):
            setattr(outfit, field, "")
            cleared.append(field)
    return cleared


@lru_cache(maxsize=1)
def _camera_rules() -> dict:
    path = Path(__file__).resolve().parents[1] / "content" / "camera_pack" / "camera_rules.yaml"
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def apply_camera_conflicts(state, warnings: list[str]) -> None:
    """Camera lens auto-fixes for poses."""
    cam = state.camera
    rules = _camera_rules()

    for fix in rules.get("lens_pose_fixes") or []:
        if cam.lens == fix.get("lens_id") and state.pose in set(fix.get("pose_ids") or ()):
            cam.lens = fix.get("target_lens_id", "")
            warnings.append(fix.get("message", "Lens adjusted for pose compatibility."))


@lru_cache(maxsize=1)
def _lighting_rules() -> dict:
    path = Path(__file__).resolve().parents[1] / "content" / "lighting_pack" / "lighting_rules.yaml"
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=1)
def _fetish_rules() -> dict:
    path = Path(__file__).resolve().parents[1] / "content" / "fetish_pack" / "fetish_rules.yaml"
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=1)
def _fetish_subgroup_by_id() -> dict[str, str]:
    rules = _fetish_rules()
    mapping: dict[str, str] = {}
    for subgroup, ids in (rules.get("subgroups") or {}).items():
        for item_id in ids:
            mapping[item_id] = subgroup
    return mapping


@lru_cache(maxsize=1)
def _fetish_conflict_groups() -> list[list[str]]:
    path = Path(__file__).resolve().parents[1] / "content" / "fetish_pack" / "conflicts.yaml"
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [group.get("ids") or [] for group in data.get("groups") or []]


def _resolve_fetish_exclusive_groups(elements: list[str], groups: list[list[str]]) -> list[str]:
    result = list(elements)
    for group in groups:
        active = [item_id for item_id in result if item_id in group]
        if len(active) <= 1:
            continue
        for item_id in active[1:]:
            result.remove(item_id)
    return result


def apply_fetish_conflicts(fetish, warnings: list[str]) -> None:
    """Trim fetish elements and resolve exclusive groups."""
    rules = _fetish_rules()
    subgroup_map = _fetish_subgroup_by_id()
    max_per_subgroup = int(rules.get("max_per_subgroup") or 6)
    max_elements = int(rules.get("max_elements") or 5)

    counts: dict[str, int] = {}
    trimmed: list[str] = []
    for item_id in fetish.elements:
        subgroup = subgroup_map.get(item_id, "")
        if counts.get(subgroup, 0) >= max_per_subgroup:
            continue
        counts[subgroup] = counts.get(subgroup, 0) + 1
        trimmed.append(item_id)
    if len(trimmed) < len(fetish.elements):
        warnings.append(f"Fetish elements trimmed to {max_per_subgroup} per subgroup.")

    conflict_groups = list(_fetish_conflict_groups())
    before = list(trimmed)
    trimmed = _resolve_fetish_exclusive_groups(trimmed, conflict_groups)
    if len(trimmed) < len(before):
        warnings.append("Conflicting fetish elements removed (exclusive group).")

    if len(trimmed) > max_elements:
        if len(fetish.elements) > max_elements:
            warnings.append(
                f"More than {max_elements} fetish elements often dilutes the scene — consider trimming."
            )
        trimmed = trimmed[:max_elements]
        warnings.append(f"Fetish elements trimmed to {max_elements} total.")

    fetish.elements = trimmed

    for rule in rules.get("compatibility_warnings") or []:
        element_ids = rule.get("element_ids") or []
        if not element_ids:
            continue
        active = [item_id for item_id in element_ids if item_id in fetish.elements]
        if len(active) >= 2:
            warnings.append(rule["message"])
        elif len(active) == 1 and len(element_ids) == 1:
            if rule["message"].startswith("Ahegao face"):
                warnings.append(rule["message"])


def apply_style_conflicts(state, warnings: list[str]) -> None:
    """Trim style selections and emit compatibility warnings."""
    style = state.style
    if not style.enabled:
        style.art_style = ""
        style.artist_style = ""
        style.quality = []
        style.aesthetic = []
        style.technique = []
        return

    rules = _style_rules()
    limits = rules.get("multi_select_limits") or {}
    for field, max_count in limits.items():
        values = getattr(style, field, None)
        if not isinstance(values, list) or len(values) <= int(max_count):
            continue
        setattr(style, field, values[: int(max_count)])
        warnings.append(f"Style {field.replace('_', ' ')} trimmed to {max_count} tags.")

    anime_ids = set((rules.get("exclusive_art_style_groups") or [[]])[0])
    realistic_quality = {"photorealistic", "hyperrealistic", "realistic"}
    if style.art_style in anime_ids and realistic_quality.intersection(style.quality):
        warnings.append("Anime art style with photorealistic quality tags usually conflict.")

    sensual = {"lewd", "erotic", "provocative"}
    if sensual.intersection(style.aesthetic) and not state.lighting.nsfw and not state.lighting.light_type:
        warnings.append("Lewd / erotic aesthetics pair better with low-key or dramatic lighting.")

    tasteful = {"tasteful_sensual", "intimate"}
    if tasteful.intersection(style.aesthetic) or "elegant" in style.aesthetic:
        if state.lighting.light_type in ("high_key_lighting",):
            warnings.append("Tasteful sensual / elegant aesthetics work best with soft lighting.")


@lru_cache(maxsize=1)
def _style_rules() -> dict:
    path = Path(__file__).resolve().parents[1] / "content" / "style_pack" / "style_rules.yaml"
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def apply_lighting_conflicts(state, warnings: list[str]) -> None:
    """Lighting pack-local auto-fixes (cross-category rules live in cross_rules.yaml)."""
    return


@lru_cache(maxsize=1)
def _appearance_rules() -> dict:
    path = Path(__file__).resolve().parents[1] / "content" / "appearance_pack" / "appearance_rules.yaml"
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=1)
def _dress_subgroup_by_id() -> dict[str, str]:
    rules = _outfit_rules()
    mapping: dict[str, str] = {}
    for subgroup, ids in (rules.get("dress_subgroups") or {}).items():
        for item_id in ids:
            mapping[item_id] = subgroup
    return mapping


@lru_cache(maxsize=1)
def _pose_rules() -> dict:
    path = Path(__file__).resolve().parents[1] / "content" / "pose_pack" / "pose_rules.yaml"
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=1)
def _couple_pose_ids() -> set[str]:
    rules = _pose_rules()
    return set(rules.get("couple_pose_ids") or ())


def is_couple_pose(pose_id: str) -> bool:
    return pose_id in _couple_pose_ids()


def apply_pose_conflicts(state, warnings: list[str]) -> None:
    """Single pose only; couple poses require group mode."""
    if not state.pose:
        return
    if is_couple_pose(state.pose) and not state.group_mode:
        state.pose = ""
        warnings.append("Couple pose cleared: requires group mode (non-solo character).")


def apply_appearance_conflicts(appearance, warnings: list[str]) -> None:
    """Resolve hair/makeup/accessories conflicts."""
    rules = _appearance_rules()
    complex_hair = set(rules.get("complex_hairstyles") or ())
    voluminous_hats = set(rules.get("voluminous_hats") or ())
    max_accessories = int(rules.get("max_accessories") or 4)
    max_makeup = int(rules.get("max_makeup") or 6)

    if appearance.hair in complex_hair and appearance.accessories:
        blocked = [a for a in appearance.accessories if a in voluminous_hats]
        if blocked:
            appearance.accessories = [a for a in appearance.accessories if a not in voluminous_hats]
            warnings.append("Voluminous hat removed due to complex hairstyle compatibility.")

    if len(appearance.accessories) > max_accessories:
        appearance.accessories = appearance.accessories[:max_accessories]
        warnings.append(f"Accessories trimmed to {max_accessories} items.")

    if len(appearance.makeup) > max_makeup:
        appearance.makeup = appearance.makeup[:max_makeup]
        warnings.append(f"Makeup trimmed to {max_makeup} items.")


def apply_outfit_conflicts(outfit, warnings: list[str]) -> None:
    """Resolve outfit-layer conflicts to avoid incoherent combinations."""
    rules = _outfit_rules()
    bottom_map = _bottom_subgroup_by_id()
    dress_map = _dress_subgroup_by_id()
    dress_layer = set(rules.get("dress_layer_subgroups") or ())
    voluminous_dresses = set(rules.get("voluminous_dresses") or ())
    bulky_jackets = set(rules.get("bulky_jackets") or ())
    long_capes = set(rules.get("long_capes") or ())

    dress_subgroup = dress_map.get(outfit.dress) if _outfit_item_active(outfit.dress) else None
    dress_is_layerable = dress_subgroup in dress_layer

    if _outfit_item_active(outfit.dress):
        if dress_is_layerable:
            cleared = _clear_fields(outfit, ("bottom",))
            if cleared:
                warnings.append("Bottom cleared: layerable dress replaces separate bottom.")
        else:
            cleared = _clear_fields(outfit, ("top", "bottom", "underwear_layer", "legwear"))
            if cleared:
                warnings.append("Top/Bottom/Legwear cleared because Dress covers the full silhouette.")

    if outfit.bottom == OUTFIT_NONE_ID:
        bottom_subgroup = OUTFIT_NONE_ID
    else:
        bottom_subgroup = bottom_map.get(outfit.bottom)
    layerable = set(rules.get("layerable_bottom_subgroups") or ("skirts", "shorts"))

    if bottom_subgroup == "long_pants":
        if _outfit_item_active(outfit.underwear_layer):
            outfit.underwear_layer = ""
            warnings.append("Underwear layer removed: long pants cover the legs.")
        if _outfit_item_active(outfit.legwear):
            outfit.legwear = ""
            warnings.append("Legwear removed: not compatible with long pants.")

    if bottom_subgroup == "underwear":
        if _outfit_item_active(outfit.underwear_layer):
            outfit.underwear_layer = ""
            warnings.append("Underwear layer cleared: bottom is already underwear-only.")

    if (
        bottom_subgroup not in layerable
        and bottom_subgroup != OUTFIT_NONE_ID
        and _outfit_item_active(outfit.underwear_layer)
        and not dress_is_layerable
    ):
        outfit.underwear_layer = ""
        warnings.append("Underwear layer only allowed with skirts or shorts.")

    if outfit.dress in voluminous_dresses and _outfit_item_active(outfit.jacket) and outfit.jacket in bulky_jackets:
        outfit.jacket = ""
        warnings.append("Bulky jacket removed to avoid overload with voluminous dress.")

    if _outfit_item_active(outfit.cape) and outfit.cape in long_capes and _outfit_item_active(outfit.jacket) and outfit.jacket in bulky_jackets:
        outfit.cape = ""
        warnings.append("Long cape removed to avoid overload with bulky jacket.")

    _sync_outfit_conditions(outfit, bottom_map)


def _sync_outfit_conditions(outfit, bottom_map: dict[str, str]) -> None:
    """Drop clothing conditions when the base garment is missing or incompatible."""
    conditions = outfit.conditions or {}
    if not _outfit_item_active(outfit.dress) and conditions.get("dress"):
        conditions["dress"] = ""
    if not _outfit_item_active(outfit.top) and conditions.get("top"):
        conditions["top"] = ""
    if not _outfit_item_active(outfit.jacket) and conditions.get("jacket"):
        conditions["jacket"] = ""
    if not _outfit_item_active(outfit.legwear) and conditions.get("legwear"):
        conditions["legwear"] = ""
    if not _outfit_item_active(outfit.underwear_layer) and conditions.get("underwear_layer"):
        bottom_subgroup = bottom_map.get(outfit.bottom)
        if bottom_subgroup != "underwear":
            conditions["underwear_layer"] = ""
    if outfit.bottom == OUTFIT_NONE_ID:
        bottom_subgroup = OUTFIT_NONE_ID
    else:
        bottom_subgroup = bottom_map.get(outfit.bottom)
    if bottom_subgroup != "long_pants" and conditions.get("bottom"):
        conditions["bottom"] = ""
    outfit.conditions = conditions


def apply_cross_category_rules(state: PromptState, warnings: list[str]) -> None:
    """Unified cross-category penalties and soft combo hints from cross_rules.yaml."""
    from egodary.core.rule_matching import format_rule_message, iter_cross_bonuses, iter_cross_penalties

    for rule in iter_cross_penalties(state, emit_warning=True):
        if rule.get("severity") == "hard_block":
            clear_path = rule.get("clear")
            if clear_path:
                _set_state_path(state, clear_path, "")
        warnings.append(format_rule_message(rule))

    for rule in iter_cross_bonuses(state):
        warnings.append(format_rule_message(rule, bonus=True))


def preview_state_conflicts(state: PromptState) -> list[str]:
    """Return conflict warnings for the current selection without mutating caller state."""
    _, warnings = apply_state_conflicts(state)
    return warnings


def apply_state_conflicts(state: PromptState) -> tuple[PromptState, list[str]]:
    """Return a resolved copy of prompt state and applied warnings."""
    state = state.model_copy(deep=True)
    warnings: list[str] = []
    apply_environment_conflicts(state, warnings)
    apply_style_conflicts(state, warnings)
    apply_outfit_conflicts(state.outfit, warnings)
    apply_pose_conflicts(state, warnings)
    apply_appearance_conflicts(state.appearance, warnings)
    apply_camera_conflicts(state, warnings)
    apply_lighting_conflicts(state, warnings)
    apply_fetish_conflicts(state.fetish, warnings)
    apply_cross_category_rules(state, warnings)
    return state, warnings


def resolve_fetish_exclusive_elements(elements: list[str], groups: list[list[str]]) -> list[str]:
    """Within a conflict group keep only the first selected element."""
    return _resolve_fetish_exclusive_groups(elements, groups)
