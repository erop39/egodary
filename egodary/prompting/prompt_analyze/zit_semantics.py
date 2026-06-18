"""Extract ZitSemantics from JSON prompt v1.2."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from egodary.prompting.prompt_analyze.json_schema import positive_block, primary_subject, split_tags
from egodary.prompting.prompt_analyze.zit_lexicon import (
    TokenClass,
    classify_token,
    extract_subject_count_tags,
    strip_meta_tags,
    subject_opener_from_count_tags,
    transform_token_for_prose,
)

HAIR_COLOR_PATTERN = re.compile(
    r"\b(black|blonde|blond|red|silver|white|blue|green|pink|purple|brown|auburn|golden|cyan|orange)"
    r"\s+(hair|haired)\b",
    re.I,
)
EYE_COLOR_PATTERN = re.compile(
    r"\b(blue|green|golden|gold|brown|red|purple|amber|hazel|grey|gray|cyan)\s+eyes\b",
    re.I,
)


@dataclass
class ZitSemantics:
    subject_opener: str = ""
    pose_action_view: list[str] = field(default_factory=list)
    appearance: list[str] = field(default_factory=list)
    outfit: list[str] = field(default_factory=list)
    scene: list[str] = field(default_factory=list)
    lighting_atmosphere_mood: list[str] = field(default_factory=list)
    camera_composition_focus: list[str] = field(default_factory=list)
    materials_textures: list[str] = field(default_factory=list)
    style_render_hint: str = ""
    nsfw_neutral: list[str] = field(default_factory=list)
    conflicts: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _dedupe(parts: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for part in parts:
        key = part.lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(part.strip())
    return out


def _resolve_hair_color(tokens: list[str]) -> tuple[list[str], list[dict[str, str]]]:
    matches: list[tuple[int, str]] = []
    hetero = any("heterochromia" in t.lower() for t in tokens)
    for i, token in enumerate(tokens):
        m = HAIR_COLOR_PATTERN.search(token)
        if m:
            matches.append((i, token))
    if len(matches) <= 1:
        return tokens, []
    kept_idx, kept = matches[0]
    dropped = [t for i, t in matches[1:]]
    if hetero:
        return tokens, []
    filtered = [t for i, t in enumerate(tokens) if i == kept_idx or t not in dropped]
    conflicts = [
        {"field": "hair_color", "kept": kept, "dropped": d, "reason": "first_explicit_wins"}
        for d in dropped
    ]
    return filtered, conflicts


def _resolve_eye_color(tokens: list[str]) -> tuple[list[str], list[dict[str, str]]]:
    if any("heterochromia" in t.lower() for t in tokens):
        return tokens, []
    matches = [t for t in tokens if EYE_COLOR_PATTERN.search(t)]
    if len(matches) <= 1:
        return tokens, []
    kept = matches[0]
    dropped = matches[1:]
    filtered = [t for t in tokens if t not in dropped]
    conflicts = [
        {"field": "eye_color", "kept": kept, "dropped": d, "reason": "first_explicit_wins"}
        for d in dropped
    ]
    return filtered, conflicts


def _collect_raw_tokens(json_prompt: dict[str, Any]) -> list[str]:
    pos = positive_block(json_prompt)
    subject = primary_subject(json_prompt)
    tokens: list[str] = []
    count_tags = list((subject.get("attributes") or {}).get("count_tags") or [])
    tokens.extend(count_tags)
    for key in ("description", "position", "action", "expression", "clothing", "clothing_state", "body_details"):
        tokens.extend(split_tags(subject.get(key)))
    scene = pos.get("scene") or {}
    for key in ("location", "time_of_day", "weather", "environment_details"):
        tokens.extend(split_tags(scene.get(key)))
    style = pos.get("style") or {}
    tokens.extend(style.get("quality_tags") or [])
    for key in ("art_style", "artist", "rendering"):
        tokens.extend(split_tags(style.get(key)))
    tokens.extend(split_tags(pos.get("lighting")))
    cam = pos.get("camera") or {}
    for key in ("shot_type", "angle", "lens", "depth_of_field"):
        tokens.extend(split_tags(cam.get(key)))
    tokens.extend(split_tags(pos.get("composition")))
    tokens.extend(split_tags(pos.get("mood")))
    tokens.extend(pos.get("color_palette") or [])
    nsfw = json_prompt.get("nsfw") or {}
    tokens.extend(nsfw.get("focus") or [])
    return tokens


def _route_token(token: str, semantics: ZitSemantics) -> None:
    prose = transform_token_for_prose(token)
    if prose is None:
        return
    kind = classify_token(token)
    if kind == TokenClass.APPEARANCE_FEATURE or (
        kind == TokenClass.VISUAL
        and any(
            m in token.lower()
            for m in ("hair", "eyes", "skin", "lips", "face", "breast", "figure", "silhouette", "bangs", "expression", "smile")
        )
    ):
        semantics.appearance.append(prose)
    elif kind == TokenClass.ACCESSORY or (
        kind == TokenClass.VISUAL
        and any(m in token.lower() for m in ("dress", "shirt", "skirt", "pants", "coat", "uniform", "outfit", "wear", "gown"))
    ):
        semantics.outfit.append(prose)
    elif kind == TokenClass.NSFW_SENSUAL:
        semantics.nsfw_neutral.append(prose)
    elif kind in (TokenClass.CAMERA_VIEW,):
        semantics.pose_action_view.append(prose)
        semantics.camera_composition_focus.append(prose)
    elif kind == TokenClass.LIGHTING:
        semantics.lighting_atmosphere_mood.append(prose)
    elif kind == TokenClass.SCENE:
        semantics.scene.append(prose)
    elif kind == TokenClass.MATERIAL:
        semantics.materials_textures.append(prose)
    elif kind == TokenClass.POSE_ACTION:
        semantics.pose_action_view.append(prose)
    elif kind == TokenClass.QUALITY_AS_DESCRIPTION:
        semantics.materials_textures.append(prose)
    else:
        low = token.lower()
        if any(m in low for m in ("angle", "shot", "focus", "framing", "lens", "depth of field", "composition")):
            semantics.camera_composition_focus.append(prose)
        elif any(m in low for m in ("light", "bloom", "spotlight", "atmosphere", "mood", "palette")):
            semantics.lighting_atmosphere_mood.append(prose)
        elif any(m in low for m in ("gallery", "interior", "room", "wall", "painting", "environment", "background")):
            semantics.scene.append(prose)
        elif any(m in low for m in ("satin", "fabric", "ribbon", "texture", "highlights")):
            semantics.materials_textures.append(prose)
        else:
            semantics.appearance.append(prose)


def extract_zit_semantics(json_prompt: dict[str, Any]) -> ZitSemantics:
    semantics = ZitSemantics()
    subject = primary_subject(json_prompt)
    pos = positive_block(json_prompt)
    raw_tokens = _collect_raw_tokens(json_prompt)

    count_tags = extract_subject_count_tags(raw_tokens)
    if not count_tags:
        count_tags = list((subject.get("attributes") or {}).get("count_tags") or [])
    semantics.subject_opener = subject_opener_from_count_tags(count_tags)

    cleaned = strip_meta_tags(raw_tokens)
    cleaned, hair_conflicts = _resolve_hair_color(cleaned)
    cleaned, eye_conflicts = _resolve_eye_color(cleaned)
    semantics.conflicts.extend(hair_conflicts)
    semantics.conflicts.extend(eye_conflicts)

    for token in cleaned:
        _route_token(token, semantics)

    style = pos.get("style") or {}
    art_style = (style.get("art_style") or "").strip()
    rendering = (style.get("rendering") or "").strip()
    if art_style:
        low = art_style.lower()
        if "realistic" in low or "photoreal" in low:
            semantics.style_render_hint = "realistic"
        elif "anime" in low or "illustration" in low:
            semantics.style_render_hint = "anime illustration"
        else:
            semantics.style_render_hint = art_style
    elif rendering:
        semantics.style_render_hint = rendering

    for key in ("pose_action_view", "appearance", "outfit", "scene", "lighting_atmosphere_mood", "camera_composition_focus", "materials_textures", "nsfw_neutral"):
        setattr(semantics, key, _dedupe(getattr(semantics, key)))

    return semantics
