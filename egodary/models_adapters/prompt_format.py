"""Shared helpers for model-specific prompt formatting from bucket maps."""

from __future__ import annotations

from egodary.core.models import PromptBuckets


def split_tag_parts(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def dedupe_tags_preserve_order(
    tags: list[str],
    *,
    case_insensitive: bool = True,
    lowercase: bool = False,
) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for raw in tags:
        normalized = raw.strip()
        if not normalized:
            continue
        if lowercase:
            normalized = normalized.lower()
        key = normalized.lower() if case_insensitive else normalized
        if key in seen:
            continue
        seen.add(key)
        unique.append(normalized)
    return unique


def format_buckets_as_tag_string(
    buckets: PromptBuckets,
    *,
    bucket_order: list[str],
    separator: str = ", ",
    dedupe_tags: bool = True,
    tag_case: str | None = "lower",
    suffix_tags: list[str] | None = None,
) -> str:
    bucket_map = buckets.model_dump()
    if "style" not in bucket_order:
        bucket_map["extra"] = [*bucket_map.get("extra", []), *bucket_map.get("style", [])]
    # Allow config-level aliases without duplicating core bucket structures.
    bucket_map["hair"] = bucket_map.get("hair") or bucket_map.get("appearance", [])
    bucket_map["makeup"] = bucket_map.get("makeup", [])
    bucket_map["scene_combined"] = [*bucket_map.get("situation", []), *bucket_map.get("scene", [])]
    tags: list[str] = []
    for key in bucket_order:
        source_key = "scene_combined" if key == "scene" and "situation" not in bucket_order else key
        for raw in bucket_map.get(source_key) or []:
            if isinstance(raw, str):
                tags.extend(split_tag_parts(raw))
    if suffix_tags:
        tags.extend(split_tag_parts(", ".join(suffix_tags)))
    unique = dedupe_tags_preserve_order(
        tags,
        case_insensitive=dedupe_tags,
        lowercase=tag_case == "lower",
    )
    return separator.join(unique)


DEFAULT_ILLUSTRIOUS_BUCKET_ORDER = [
    "quality",
    "subject",
    "character",
    "face",
    "hair",
    "makeup",
    "outfit",
    "pose",
    "scene",
    "lighting",
    "atmosphere",
    "style",
    "fetish",
    "extra",
    "camera",
]
