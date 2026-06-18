"""Render structured JSON prompt (v1.2) into model-specific text."""

from __future__ import annotations

from typing import Any

from egodary.core.pipeline import PromptEngine
from egodary.prompting.prompt_analyze.json_schema import (
    dedupe_tags,
    join_tags,
    negative_to_string,
    positive_block,
    primary_subject,
    split_tags,
)
from egodary.prompting.prompt_analyze.zit_renderer import ZitRenderResult, render_zimage_turbo_v11


def _subject_tag_lists(subject: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "description": split_tags(subject.get("description")),
        "position": split_tags(subject.get("position")),
        "action": split_tags(subject.get("action")),
        "expression": split_tags(subject.get("expression")),
        "clothing": split_tags(subject.get("clothing")),
        "clothing_state": split_tags(subject.get("clothing_state")),
        "body_details": split_tags(subject.get("body_details")),
    }


def _scene_tags(pos: dict[str, Any]) -> list[str]:
    scene = pos.get("scene") or {}
    parts: list[str] = []
    for key in ("location", "time_of_day", "weather", "environment_details"):
        parts.extend(split_tags(scene.get(key)))
    return parts


def _style_tags(pos: dict[str, Any]) -> tuple[list[str], list[str]]:
    style = pos.get("style") or {}
    quality = list(style.get("quality_tags") or [])
    style_parts: list[str] = []
    for key in ("art_style", "artist", "rendering"):
        style_parts.extend(split_tags(style.get(key)))
    return quality, style_parts


def _camera_tags(pos: dict[str, Any]) -> list[str]:
    cam = pos.get("camera") or {}
    parts: list[str] = []
    for key in ("shot_type", "angle", "lens", "depth_of_field"):
        parts.extend(split_tags(cam.get(key)))
    parts.extend(split_tags(pos.get("composition")))
    return parts


def _atmosphere_tags(pos: dict[str, Any]) -> list[str]:
    parts = split_tags(pos.get("mood"))
    parts.extend(pos.get("color_palette") or [])
    return [str(p) for p in parts if str(p).strip()]


def _nsfw_tags(json_prompt: dict[str, Any]) -> list[str]:
    nsfw = json_prompt.get("nsfw") or {}
    return [str(p) for p in (nsfw.get("focus") or []) if str(p).strip()]


def _count_tags_from_json(json_prompt: dict[str, Any]) -> list[str]:
    subject = primary_subject(json_prompt)
    return list((subject.get("attributes") or {}).get("count_tags") or [])


def render_illustrious(json_prompt: dict[str, Any]) -> tuple[str, str]:
    """Danbooru-style comma tags — order: quality → subjects → scene → style → lighting → camera → mood → nsfw."""
    pos = positive_block(json_prompt)
    quality, style_tags = _style_tags(pos)
    parts: list[str] = list(quality)
    parts.extend(_count_tags_from_json(json_prompt))

    for subject in pos.get("subjects") or []:
        if not isinstance(subject, dict):
            continue
        fields = _subject_tag_lists(subject)
        for key in (
            "description",
            "position",
            "action",
            "expression",
            "clothing",
            "clothing_state",
            "body_details",
        ):
            parts.extend(fields[key])

    parts.extend(_scene_tags(pos))
    parts.extend(style_tags)
    parts.extend(split_tags(pos.get("lighting")))
    parts.extend(_camera_tags(pos))
    parts.extend(_atmosphere_tags(pos))
    parts.extend(_nsfw_tags(json_prompt))

    positive = join_tags(dedupe_tags(parts))
    negative = negative_to_string(json_prompt.get("negative"))
    return positive, negative


def render_anima(json_prompt: dict[str, Any], engine: PromptEngine) -> tuple[str, str]:
    """14-block structured output — artistic sections separated per Anima adapter rules."""
    adapter = engine.get_adapter("anima")
    pos = positive_block(json_prompt)
    subject = primary_subject(json_prompt)
    fields = _subject_tag_lists(subject)
    quality, style_tags = _style_tags(pos)

    description = fields["description"]
    expression = fields["expression"]
    hair_misc = [t for t in description if any(m in t.lower() for m in ("hair", "bangs", "makeup", "lip"))]
    body = fields["body_details"] + [
        t for t in description if any(m in t.lower() for m in ("body", "breast", "skin", "figure", "athletic"))
    ]
    subject_core = [t for t in description if t not in hair_misc and t not in body]
    if not subject_core:
        subject_core = description[:4]
    count_tags = _count_tags_from_json(json_prompt)

    blocks = [
        join_tags(quality),
        join_tags(style_tags) or "anime style",
        join_tags(count_tags + subject_core) or "1girl, solo",
        join_tags(body) or "athletic body",
        join_tags(expression + (["detailed face"] if expression else [])),
        join_tags(hair_misc) or "detailed hair",
        join_tags(fields["clothing"] + fields["clothing_state"]) or "cohesive outfit design",
        join_tags(fields["action"] + fields["position"]) or "natural pose",
        join_tags(_camera_tags(pos)) or "upper body, portrait framing",
        join_tags(_scene_tags(pos)) or "stylized environment",
        join_tags(split_tags(pos.get("lighting"))) or "soft natural lighting",
        join_tags(_atmosphere_tags(pos)) or "clean atmospheric depth",
        join_tags(_nsfw_tags(json_prompt)),
        "clean anatomy, coherent composition",
    ]
    cleaned = [adapter._sanitize_block(block) for block in blocks if block.strip()]  # noqa: SLF001
    positive = "\n\n".join(cleaned)
    negative = adapter.negative_prompt() or negative_to_string(json_prompt.get("negative"))
    custom_neg = negative_to_string(json_prompt.get("negative"))
    if custom_neg and custom_neg != negative_to_string(None):
        negative = join_tags(dedupe_tags(split_tags(negative) + split_tags(custom_neg)))
    return positive, negative


def render_zimage_turbo(json_prompt: dict[str, Any]) -> tuple[str, str]:
    """Natural-language narrative for Z-Image Turbo (v1.1 rule-based)."""
    result = render_zimage_turbo_v11(json_prompt)
    return result.text, ""


def render_zimage_turbo_full(json_prompt: dict[str, Any], *, use_llm: bool = False) -> ZitRenderResult:
    from egodary.prompting.prompt_analyze.zit_llm_refine import zit_llm_refine

    draft = render_zimage_turbo_v11(json_prompt)
    if not use_llm:
        return draft
    refined = zit_llm_refine(draft, use_llm=True)
    return refined.result


def render_json_for_model(
    json_prompt: dict[str, Any],
    target_model: str,
    engine: PromptEngine,
) -> tuple[str, str]:
    model = target_model if target_model in {"illustrious", "anima", "zimage_turbo"} else "illustrious"
    if model == "anima":
        return render_anima(json_prompt, engine)
    if model == "zimage_turbo":
        return render_zimage_turbo(json_prompt)
    return render_illustrious(json_prompt)
