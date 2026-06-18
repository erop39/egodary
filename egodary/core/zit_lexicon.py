"""Tag classification and phrase mapping for Z-Image Turbo prose (convert + assemble)."""

from __future__ import annotations

import re
from enum import Enum
from typing import Iterable

from egodary.core.quality_boosters import is_score_rating_tag


class TokenClass(str, Enum):
    META_QUALITY = "meta_quality"
    SUBJECT_COUNT = "subject_count"
    QUALITY_AS_DESCRIPTION = "quality_as_description"
    EVALUATIVE = "evaluative"
    APPEARANCE_FEATURE = "appearance_feature"
    ACCESSORY = "accessory"
    NSFW_SENSUAL = "nsfw_sensual"
    CAMERA_VIEW = "camera_view"
    LIGHTING = "lighting"
    SCENE = "scene"
    MATERIAL = "material"
    POSE_ACTION = "pose_action"
    VISUAL = "visual"


META_QUALITY_EXACT = frozenset(
    {
        "masterpiece",
        "best quality",
        "high quality",
        "worst quality",
        "low quality",
        "normal quality",
        "highres",
        "absurdres",
        "uncensored",
        "8k",
        "uhd",
        "ultra detailed",
        "very detailed",
        "extremely detailed",
        "intricate details",
        "sharp focus",
        "high resolution",
        "professional illustration",
        "high-end anime production quality",
        "clean anatomy",
        "coherent composition",
    }
)

SUBJECT_COUNT_PATTERNS = (
    (re.compile(r"^1girl$", re.I), "1girl"),
    (re.compile(r"^2girls$", re.I), "2girls"),
    (re.compile(r"^3girls$", re.I), "3girls"),
    (re.compile(r"^1boy$", re.I), "1boy"),
    (re.compile(r"^2boys$", re.I), "2boys"),
    (re.compile(r"^solo$", re.I), "solo"),
    (re.compile(r"^couple$", re.I), "couple"),
    (re.compile(r"^multiple girls$", re.I), "multiple_girls"),
)

QUALITY_PHRASE_MAP: dict[str, str] = {
    "detailed skin": "smooth skin with subtle natural texture and soft highlights",
    "smooth skin": "smooth skin with subtle natural texture",
    "realistic": "realistic rendering",
    "photorealistic": "realistic rendering with lifelike detail",
    "semi-realistic": "semi-realistic rendering with natural detail",
    "soft bloom": "soft bloom and atmospheric depth",
    "soft spotlight": "a gentle spotlight with soft bloom",
}

EVALUATIVE_MAP: dict[str, str] = {
    "beautiful": "with refined facial features",
    "elegant": "with a graceful silhouette",
    "pretty": "with delicate facial features",
    "gorgeous": "with striking facial features",
    "cute": "with youthful delicate features",
}

APPEARANCE_FEATURE_MARKERS = (
    "cat ears",
    "fox ears",
    "animal ears",
    "fox tail",
    "cat tail",
    "tail",
    "horns",
    "heterochromia",
    "wings",
    "elf ears",
    "demon horns",
    "kemonomimi",
)

ACCESSORY_MARKERS = (
    "collar",
    "choker",
    "ribbon",
    "gloves",
    "harness",
    "necklace",
    "earring",
    "belt",
    "scarf",
    "hat",
    "veil",
    "cape",
)

NSFW_SENSUAL_MARKERS = (
    "partially unbuttoned",
    "unbuttoned",
    "wet skin",
    "cleavage",
    "erotic",
    "sensual",
    "seductive",
    "suggestive",
    "lewd",
    "nsfw",
    "exposed",
    "nipple",
    "panties",
    "lingerie",
    "slipping",
    "see-through",
    "sheer",
    "topless",
    "bottomless",
)

CAMERA_VIEW_MARKERS = (
    "side view",
    "dutch angle",
    "three-quarter",
    "three quarter",
    "low angle",
    "high angle",
    "upper body",
    "full body",
    "portrait",
    "close-up",
    "close up",
    "medium shot",
    "cowboy shot",
    "from side",
    "from behind",
    "pov",
)

LIGHTING_MARKERS = (
    "lighting",
    "light",
    "spotlight",
    "rim light",
    "backlight",
    "god rays",
    "bloom",
    "shadow",
    "highlight",
    "volumetric",
    "cinematic light",
)

SCENE_MARKERS = (
    "gallery",
    "interior",
    "room",
    "bedroom",
    "street",
    "forest",
    "beach",
    "city",
    "apartment",
    "outdoor",
    "indoor",
    "background",
    "wall",
    "window",
    "painting",
    "museum",
)

MATERIAL_MARKERS = (
    "satin",
    "silk",
    "fabric",
    "lace",
    "leather",
    "cotton",
    "velvet",
    "denim",
    "metal",
    "texture",
    "drapery",
    "flowing",
    "wet",
    "glossy",
    "matte",
)

POSE_ACTION_MARKERS = (
    "standing",
    "sitting",
    "lying",
    "walking",
    "looking",
    "touching",
    "holding",
    "leaning",
    "pose",
    "dynamic pose",
    "arms",
    "hand on",
    "chin",
)


def _normalize(token: str) -> str:
    return re.sub(r"\s+", " ", token.strip().lower())


def is_meta_quality(token: str) -> bool:
    low = _normalize(token)
    if low in META_QUALITY_EXACT or is_score_rating_tag(token):
        return True
    return any(
        low == m or low.startswith(m + ",") or low.endswith("," + m)
        for m in META_QUALITY_EXACT
    )


def is_subject_count(token: str) -> bool:
    low = _normalize(token)
    for pattern, _ in SUBJECT_COUNT_PATTERNS:
        if pattern.match(low):
            return True
    return False


def extract_subject_count_tags(tokens: Iterable[str]) -> list[str]:
    found: list[str] = []
    for token in tokens:
        low = _normalize(token)
        for pattern, label in SUBJECT_COUNT_PATTERNS:
            if pattern.match(low):
                found.append(label)
                break
    return found


def subject_opener_from_count_tags(count_tags: list[str]) -> str:
    tags = {_normalize(t) for t in count_tags}
    if "2girls" in tags or "couple" in tags:
        return "Two women"
    if "3girls" in tags or "multiple_girls" in tags:
        return "Three women"
    if "1boy" in tags:
        return "A young man" if "solo" in tags else "A man"
    if "2boys" in tags:
        return "Two men"
    if "1girl" in tags or "solo" in tags or not tags:
        return "A young woman" if "solo" in tags or "1girl" in tags else "A woman"
    return "A figure"


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    low = _normalize(text)
    return any(m in low for m in markers)


def classify_token(token: str) -> TokenClass:
    if is_meta_quality(token):
        return TokenClass.META_QUALITY
    if is_subject_count(token):
        return TokenClass.SUBJECT_COUNT
    low = _normalize(token)
    if low in QUALITY_PHRASE_MAP:
        return TokenClass.QUALITY_AS_DESCRIPTION
    if low in EVALUATIVE_MAP:
        return TokenClass.EVALUATIVE
    if _contains_any(token, APPEARANCE_FEATURE_MARKERS):
        return TokenClass.APPEARANCE_FEATURE
    if _contains_any(token, NSFW_SENSUAL_MARKERS):
        return TokenClass.NSFW_SENSUAL
    if _contains_any(token, ACCESSORY_MARKERS):
        return TokenClass.ACCESSORY
    if _contains_any(token, CAMERA_VIEW_MARKERS):
        return TokenClass.CAMERA_VIEW
    if _contains_any(token, LIGHTING_MARKERS):
        return TokenClass.LIGHTING
    if _contains_any(token, MATERIAL_MARKERS):
        return TokenClass.MATERIAL
    if _contains_any(token, SCENE_MARKERS):
        return TokenClass.SCENE
    if _contains_any(token, POSE_ACTION_MARKERS):
        return TokenClass.POSE_ACTION
    return TokenClass.VISUAL


def map_quality_phrase(token: str) -> str | None:
    return QUALITY_PHRASE_MAP.get(_normalize(token))


def map_evaluative_phrase(token: str) -> str | None:
    return EVALUATIVE_MAP.get(_normalize(token))


def transform_token_for_prose(token: str) -> str | None:
    """Return prose phrase or None if token should be dropped."""
    kind = classify_token(token)
    if kind == TokenClass.META_QUALITY or kind == TokenClass.SUBJECT_COUNT:
        return None
    if kind == TokenClass.QUALITY_AS_DESCRIPTION:
        return map_quality_phrase(token) or token
    if kind == TokenClass.EVALUATIVE:
        return map_evaluative_phrase(token) or token
    return token.strip()


def strip_meta_tags(tokens: Iterable[str]) -> list[str]:
    return [t for t in tokens if classify_token(t) not in (TokenClass.META_QUALITY, TokenClass.SUBJECT_COUNT)]
