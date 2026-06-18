"""Convert free-text prompts into structured JSON (schema v1.2, grok_report rules)."""

from __future__ import annotations

from typing import Any

from egodary.core.importer import import_prompt_with_report
from egodary.core.models import PromptState
from egodary.core.pipeline import PromptEngine
from egodary.core.runtime_registry import RuntimeRegistry
from egodary.prompting.prompt_analyze.input_format import PromptFormat, detect_prompt_format
from egodary.prompting.prompt_analyze.json_schema import (
    JSON_SCHEMA_VERSION,
    categorize_negative,
    dedupe_tags,
    join_tags,
    nsfw_intensity,
    split_positive_negative,
    try_parse_json_prompt,
)
from egodary.core.quality_boosters import is_score_rating_tag
from egodary.prompting.prompt_analyze.normalize_weights import normalize_weights
from egodary.prompting.prompt_analyze.zit_lexicon import extract_subject_count_tags, is_subject_count

__all__ = [
    "JSON_SCHEMA_VERSION",
    "convert_to_json",
    "state_to_json_prompt",
    "try_parse_json_prompt",
]


def _resolve(engine: PromptEngine, category_id: str, item_id: str, model_id: str) -> str | None:
    if not item_id:
        return None
    return engine._resolve_selection(item_id, category_id, model_id)


def _subject_from_state(
    engine: PromptEngine,
    state: PromptState,
    buckets,
    *,
    character=None,
    is_secondary: bool = False,
) -> dict[str, Any]:
    model_id = state.model_id
    ch = character or state.character

    description_parts = list(buckets.subject)
    if not is_secondary:
        description_parts.extend(buckets.character)
        description_parts.extend(buckets.face)
        description_parts.extend(buckets.hair)
        description_parts.extend(buckets.makeup)
    else:
        description_parts.append("secondary character")

    char_tags: list[str] = []
    for field_name, category_id in (
        ("age_appearance", "character.age_appearance"),
        ("body_type", "character.body_type"),
        ("breast_size", "character.breast_size"),
        ("ethnicity", "character.ethnicity"),
        ("skin_tone", "character.skin_tone"),
    ):
        value = getattr(ch, field_name, "")
        if value:
            resolved = _resolve(engine, category_id, value, model_id)
            if resolved:
                char_tags.extend(engine._split_tags(resolved))

    position_parts = list(buckets.situation)
    framing = _resolve(engine, "camera.framing", state.camera.framing, model_id)
    if framing:
        position_parts.append(framing)

    action_parts = list(buckets.pose)
    if state.interaction.action:
        resolved = _resolve(engine, "interaction.action", state.interaction.action, model_id)
        if resolved:
            action_parts.extend(engine._split_tags(resolved))
        else:
            action_parts.append(state.interaction.action)

    expression_parts: list[str] = []
    if state.expression:
        expression_parts.append(state.expression)
    if not is_secondary and state.face.facial_expression:
        resolved = _resolve(engine, "face.facial_expression", state.face.facial_expression, model_id)
        if resolved:
            expression_parts.extend(engine._split_tags(resolved))

    clothing_parts = list(buckets.outfit) if not is_secondary else []
    clothing_state_parts: list[str] = []
    if not is_secondary:
        for field_name, condition_id in (state.outfit.conditions or {}).items():
            if condition_id:
                resolved = _resolve(engine, "outfit.clothing_condition", condition_id, model_id)
                if resolved:
                    clothing_state_parts.extend(engine._split_tags(resolved))

    body_detail_parts: list[str] = []
    if not is_secondary:
        for item_id in ch.body_details:
            resolved = _resolve(engine, "character.body_details", item_id, model_id)
            if resolved:
                body_detail_parts.extend(engine._split_tags(resolved))

    merged_description = dedupe_tags(description_parts + char_tags)
    count_tags = extract_subject_count_tags(merged_description)
    description_clean = [
        p for p in merged_description if not is_subject_count(p) and not is_score_rating_tag(p)
    ]

    subject: dict[str, Any] = {
        "description": join_tags(description_clean),
        "position": join_tags(dedupe_tags(position_parts)),
        "action": join_tags(dedupe_tags(action_parts)),
        "expression": join_tags(dedupe_tags(expression_parts)),
        "clothing": join_tags(dedupe_tags(clothing_parts)),
        "attributes": {"count_tags": count_tags},
    }
    if clothing_state_parts:
        subject["clothing_state"] = join_tags(dedupe_tags(clothing_state_parts))
    if body_detail_parts:
        subject["body_details"] = join_tags(dedupe_tags(body_detail_parts))
    return subject


def _scene_block(engine: PromptEngine, state: PromptState, buckets) -> dict[str, str]:
    model_id = state.model_id
    location = _resolve(engine, "scene.location", state.scene.location, model_id)
    if not location and state.environment.location:
        location = _resolve(engine, "environment.location", state.environment.location, model_id)
    time_of_day = _resolve(engine, "scene.time", state.scene.time, model_id)
    weather = _resolve(engine, "scene.weather", state.scene.weather, model_id)
    env_parts = list(buckets.scene)
    if state.scene.season:
        season = _resolve(engine, "scene.season", state.scene.season, model_id)
        if season:
            env_parts.append(season)
    for modifier_id in state.environment.modifiers:
        resolved = _resolve(engine, "environment.modifiers", modifier_id, model_id)
        if resolved:
            env_parts.extend(engine._split_tags(resolved))
    return {
        "location": location or "",
        "time_of_day": time_of_day or "",
        "weather": weather or "",
        "environment_details": join_tags(dedupe_tags(env_parts)),
    }


def _style_block(engine: PromptEngine, state: PromptState, buckets) -> dict[str, Any]:
    model_id = state.model_id
    style = state.style
    art_style = _resolve(engine, "style.art_style", style.art_style, model_id) if style.art_style else ""
    artist = _resolve(engine, "style.artist_style", style.artist_style, model_id) if style.artist_style else ""
    rendering_parts: list[str] = []
    for item_id in style.technique:
        resolved = _resolve(engine, "style.technique", item_id, model_id)
        if resolved:
            rendering_parts.extend(engine._split_tags(resolved))
    aesthetic_parts: list[str] = list(buckets.style)
    return {
        "art_style": art_style or join_tags(aesthetic_parts),
        "artist": artist or "",
        "rendering": join_tags(dedupe_tags(rendering_parts)),
        "quality_tags": dedupe_tags(list(buckets.quality)),
    }


def _camera_block(engine: PromptEngine, state: PromptState) -> dict[str, str]:
    model_id = state.model_id
    cam = state.camera
    return {
        "shot_type": _resolve(engine, "camera.framing", cam.framing, model_id) or "",
        "angle": _resolve(engine, "camera.angle", cam.angle, model_id) or "",
        "lens": _resolve(engine, "camera.lens", cam.lens, model_id) or "",
        "depth_of_field": _resolve(engine, "camera.focus", cam.focus, model_id) or "",
    }


def _parameters_block(engine: PromptEngine, model_id: str) -> dict[str, Any]:
    adapter = engine.get_adapter(model_id)
    defaults = adapter.generation_defaults()
    sampler = str(defaults.get("sampler") or "Euler a")
    return {
        "steps": int(defaults.get("steps", 30)),
        "cfg_scale": float(defaults.get("cfg", defaults.get("cfg_scale", 7.0))),
        "sampler": sampler,
        "seed": -1,
        "width": int(defaults.get("width", 1024)),
        "height": int(defaults.get("height", 1024)),
    }


def state_to_json_prompt(
    *,
    state: PromptState,
    engine: PromptEngine,
    model_target: str,
    unknown: list[str] | None = None,
    negative_text: str | None = None,
) -> dict[str, Any]:
    """Build production JSON prompt from PromptState (schema v1.2)."""
    work_state = state.model_copy(deep=True)
    work_state.model_id = model_target
    assembled = engine.assemble(work_state)
    buckets = assembled.buckets

    subjects = [_subject_from_state(engine, work_state, buckets)]
    if work_state.group_mode and work_state.characters.secondary:
        subjects.append(
            _subject_from_state(
                engine,
                work_state,
                buckets,
                character=work_state.characters.secondary,
                is_secondary=True,
            )
        )

    extra_unknown = [u for u in (unknown or []) if u.strip()]
    if extra_unknown:
        primary = subjects[0]
        extra = join_tags(extra_unknown)
        primary["description"] = join_tags([primary.get("description", ""), extra])
        primary["attributes"]["unparsed"] = extra_unknown

    lighting_text = join_tags(dedupe_tags(list(buckets.lighting)))
    composition = _resolve(engine, "camera.composition", work_state.camera.composition, model_target) or ""
    mood_parts: list[str] = []
    if work_state.mood_preset:
        mood_parts.append(work_state.mood_preset)
    if work_state.personality:
        mood_parts.append(work_state.personality)
    if work_state.atmosphere:
        mood_parts.extend(work_state.atmosphere)

    color_parts: list[str] = []
    color_mood = _resolve(engine, "lighting.color_mood", work_state.lighting.color_mood, model_target)
    if color_mood:
        color_parts.extend(engine._split_tags(color_mood))

    nsfw_focus = list(buckets.fetish)
    nsfw_light = _resolve(engine, "lighting.nsfw", work_state.lighting.nsfw, model_target)
    if nsfw_light:
        nsfw_focus.extend(engine._split_tags(nsfw_light))

    negative = categorize_negative(negative_text or assembled.negative)

    return {
        "version": JSON_SCHEMA_VERSION,
        "model_target": model_target,
        "positive": {
            "subjects": subjects,
            "scene": _scene_block(engine, work_state, buckets),
            "style": _style_block(engine, work_state, buckets),
            "lighting": lighting_text,
            "camera": _camera_block(engine, work_state),
            "composition": composition,
            "mood": join_tags(dedupe_tags(mood_parts)),
            "color_palette": dedupe_tags(color_parts),
        },
        "nsfw": {
            "intensity": nsfw_intensity(work_state.lewdness),
            "focus": dedupe_tags(nsfw_focus),
        },
        "negative": negative,
        "parameters": _parameters_block(engine, model_target),
    }


def prompt_text_to_json(
    *,
    prompt: str,
    source_model: str,
    model_target: str,
    engine: PromptEngine,
    registry: RuntimeRegistry | None = None,
) -> dict[str, Any]:
    """Parse tag/natural-language prompt into JSON intermediate (extract_core stage)."""
    positive_text, inline_negative = split_positive_negative(prompt)
    normalized = normalize_weights(positive_text)
    import_result = import_prompt_with_report(
        normalized.clean_prompt or positive_text,
        source_model,
        registry,
    )
    return state_to_json_prompt(
        state=import_result.state,
        engine=engine,
        model_target=model_target,
        unknown=import_result.unknown,
        negative_text=inline_negative,
    )


def convert_to_json(
    *,
    prompt: str,
    source_model: str = "illustrious",
    model_target: str | None = None,
    engine: PromptEngine,
    registry: RuntimeRegistry | None = None,
) -> tuple[dict[str, Any], PromptFormat]:
    """Parse text prompt and return structured JSON prompt + detected input format."""
    detected = detect_prompt_format(prompt)
    target = model_target or source_model
    existing = try_parse_json_prompt(prompt)
    if existing is not None:
        payload = existing.copy()
        payload["model_target"] = target
        return payload, "json"
    payload = prompt_text_to_json(
        prompt=prompt,
        source_model=source_model,
        model_target=target,
        engine=engine,
        registry=registry,
    )
    return payload, detected
