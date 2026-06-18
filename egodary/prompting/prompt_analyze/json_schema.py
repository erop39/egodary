"""Shared JSON prompt schema v1.2 (grok_report production rules)."""

from __future__ import annotations

import json
import re
from typing import Any

JSON_SCHEMA_VERSION = "1.2"
SUPPORTED_MODEL_TARGETS = frozenset(
    {"illustrious", "anima", "pony", "zimage_turbo", "flux"},
)

ANATOMY_NEGATIVE = frozenset(
    {
        "bad anatomy",
        "bad hands",
        "extra fingers",
        "fused fingers",
        "mutated hands",
        "missing fingers",
        "extra digit",
        "fewer digits",
        "extra limbs",
        "mutated",
    }
)
ARTIFACT_NEGATIVE = frozenset(
    {
        "blurry",
        "jpeg artifacts",
        "grainy",
        "artifacts",
        "overexposed",
        "underexposed",
        "lowres",
        "worst quality",
        "low quality",
        "normal quality",
    }
)

DEFAULT_NEGATIVE: dict[str, list[str]] = {
    "general": [
        "blurry",
        "low quality",
        "deformed",
        "bad anatomy",
        "extra limbs",
        "watermark",
        "text",
        "logo",
    ],
    "anatomy": ["bad hands", "extra fingers", "fused fingers", "mutated hands"],
    "artifacts": ["overexposed", "underexposed", "grainy", "artifacts"],
}


def join_tags(parts: list[str]) -> str:
    return ", ".join(p for p in parts if p and str(p).strip())


def split_tags(value: str | list[str] | None) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [p.strip() for p in re.split(r",\s*", str(value)) if p.strip()]


def dedupe_tags(parts: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for part in parts:
        key = str(part).lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(str(part).strip())
    return out


def nsfw_intensity(lewdness: int) -> str:
    if lewdness <= 2:
        return "low"
    if lewdness <= 4:
        return "medium"
    if lewdness <= 6:
        return "high"
    return "extreme"


def split_positive_negative(prompt: str) -> tuple[str, str | None]:
    match = re.search(
        r"\n\s*(?:negative(?:\s*prompt)?|neg)\s*:\s*",
        prompt,
        flags=re.I,
    )
    if not match:
        return prompt, None
    positive = prompt[: match.start()].strip()
    negative = prompt[match.end() :].strip()
    return positive, negative or None


def categorize_negative(text: str | None) -> dict[str, list[str]]:
    if not text:
        return {k: list(v) for k, v in DEFAULT_NEGATIVE.items()}
    tokens = split_tags(text)
    general: list[str] = []
    anatomy: list[str] = []
    artifacts: list[str] = []
    for token in tokens:
        lower = token.lower()
        if any(key in lower for key in ANATOMY_NEGATIVE):
            anatomy.append(token)
        elif any(key in lower for key in ARTIFACT_NEGATIVE):
            artifacts.append(token)
        else:
            general.append(token)
    if not general and not anatomy and not artifacts:
        return {k: list(v) for k, v in DEFAULT_NEGATIVE.items()}
    return {
        "general": general or list(DEFAULT_NEGATIVE["general"]),
        "anatomy": anatomy or list(DEFAULT_NEGATIVE["anatomy"]),
        "artifacts": artifacts or list(DEFAULT_NEGATIVE["artifacts"]),
    }


def negative_to_string(negative: dict[str, Any] | None) -> str:
    if not negative:
        return join_tags(
            DEFAULT_NEGATIVE["general"]
            + DEFAULT_NEGATIVE["anatomy"]
            + DEFAULT_NEGATIVE["artifacts"]
        )
    parts: list[str] = []
    for key in ("general", "anatomy", "artifacts"):
        parts.extend(negative.get(key) or [])
    return join_tags(dedupe_tags([str(p) for p in parts]))


def try_parse_json_prompt(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if not stripped.startswith("{"):
        return None
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    if "positive" in data and "version" in data:
        return data
    return None


def primary_subject(json_prompt: dict[str, Any]) -> dict[str, Any]:
    subjects = (json_prompt.get("positive") or {}).get("subjects") or []
    if subjects and isinstance(subjects[0], dict):
        return subjects[0]
    return {}


def positive_block(json_prompt: dict[str, Any]) -> dict[str, Any]:
    block = json_prompt.get("positive")
    return block if isinstance(block, dict) else {}
