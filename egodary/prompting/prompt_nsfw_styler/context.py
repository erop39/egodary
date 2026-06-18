"""Build LLM context for NSFW styler (mutable fragments, unknown phrases)."""

from __future__ import annotations

from egodary.core.models import PromptState
from egodary.prompting.prompt_analyze.extract_core import CorePrompt

IDENTITY_CHARACTER_PREFIX = "character."

IDENTITY_FACE_FIELDS = frozenset({
    "face.eyes",
    "face.eye_color",
    "face.skin",
    "face.face_shape",
    "face.eyebrows",
    "face.nose",
    "face.jaw_chin",
    "face.age_maturity",
    "face.beauty_archetype",
    "face.facial_details",
})

IDENTITY_APPEARANCE_FIELDS = frozenset({
    "appearance.hair",
    "appearance.hair_color",
})

NSFW_MUTABLE_SECTIONS: tuple[str, ...] = (
    "outfit",
    "pose",
    "camera",
    "lighting",
    "expression",
    "mouth_lips",
    "scene",
    "environment",
    "style",
    "fetish",
)

_MUTABLE_FIELD_PATHS: tuple[str, ...] = (
    "pose",
    "outfit.dress",
    "outfit.top",
    "outfit.bottom",
    "outfit.underwear_layer",
    "outfit.legwear",
    "outfit.jacket",
    "outfit.footwear",
    "outfit.gloves",
    "outfit.cape",
    "camera.angle",
    "camera.framing",
    "camera.composition",
    "camera.focus",
    "camera.lens",
    "camera.nsfw_shot",
    "lighting.light_type",
    "lighting.direction",
    "lighting.color_mood",
    "lighting.nsfw",
    "lighting.quality",
    "fetish.elements",
    "environment.situation",
    "environment.modifiers",
)


def is_identity_path(field_path: str) -> bool:
    if field_path.startswith(IDENTITY_CHARACTER_PREFIX):
        return True
    if field_path in IDENTITY_FACE_FIELDS:
        return True
    return field_path in IDENTITY_APPEARANCE_FIELDS


def collect_identity_buckets(core: CorePrompt | None) -> list[dict[str, str]]:
    if core is None:
        return []
    return [
        {
            "path": path,
            "value": core.locked_values.get(path, ""),
            "item_id": core.locked_values.get(f"{path}__id", ""),
        }
        for path in sorted(core.locked_paths)
        if is_identity_path(path)
    ]


def _is_locked(field_path: str, core: CorePrompt | None) -> bool:
    if core is None:
        return False
    locked = core.locked_paths
    if field_path in locked:
        return True
    return any(field_path.startswith(p.rstrip(".")) for p in locked)


def _field_value(state: PromptState, field_path: str) -> str | list[str]:
    if field_path == "pose":
        return state.pose
    section, fld = field_path.split(".", 1)
    return getattr(getattr(state, section), fld)


def collect_mutable_fragments(
    state: PromptState,
    core: CorePrompt | None = None,
    *,
    unknown_phrases: list[str] | None = None,
) -> list[str]:
    """Non-locked state fields and import leftovers safe to intensify."""
    fragments: list[str] = []
    for field_path in _MUTABLE_FIELD_PATHS:
        if _is_locked(field_path, core):
            continue
        value = _field_value(state, field_path)
        if isinstance(value, list):
            for item in value:
                if item and item != "none":
                    fragments.append(f"{field_path}: {item}")
        elif value and value != "none":
            fragments.append(f"{field_path}: {value}")

    for phrase in unknown_phrases or []:
        text = (phrase or "").strip()
        if text:
            fragments.append(f"unknown: {text}")

    if core:
        for label in core.layers.get("key_tags", []):
            fragments.append(f"key_tag: {label}")

    return fragments
