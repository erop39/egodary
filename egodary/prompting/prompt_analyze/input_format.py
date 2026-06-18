"""Detect input prompt representation before JSON normalization."""

from __future__ import annotations

import re
from typing import Literal

from egodary.prompting.prompt_analyze.json_schema import try_parse_json_prompt

PromptFormat = Literal[
    "tags",
    "structured_blocks",
    "natural_language",
    "weighted_tags",
    "json",
    "unknown",
]


def detect_prompt_format(prompt: str) -> PromptFormat:
    text = prompt.strip()
    if not text:
        return "unknown"
    if try_parse_json_prompt(text) is not None:
        return "json"
    if re.search(r"\([^()]+:[0-9]", text) or re.search(r"\[\w", text):
        return "weighted_tags"
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if len(blocks) >= 8:
        return "structured_blocks"
    if re.search(r"\b(wearing|standing|sitting|with|she has|he has)\b", text, re.I) and "." in text:
        return "natural_language"
    if "," in text or re.search(r"\b(1girl|1boy|solo|score_\d)\b", text, re.I):
        return "tags"
    return "unknown"
