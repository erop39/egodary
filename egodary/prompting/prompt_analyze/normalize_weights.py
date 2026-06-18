"""Parse and restore weighted tag syntax in prompts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_WEIGHTED_PAREN_RE = re.compile(r"\(([^():]+)(?::([0-9]*\.?[0-9]+))?\)")
_BRACKET_RE = re.compile(r"\[([^\]]+)\]")
_DOUBLE_PAREN_RE = re.compile(r"\(\(([^)]+)\)\)")


@dataclass
class WeightedTag:
    text: str
    weight: float = 1.0


@dataclass
class NormalizedPrompt:
    tokens: list[WeightedTag] = field(default_factory=list)
    clean_prompt: str = ""
    had_weights: bool = False


def _strip_outer_weights(prompt: str) -> tuple[str, list[WeightedTag], bool]:
    tokens: list[WeightedTag] = []
    had_weights = False
    work = prompt

    def repl_double(match: re.Match[str]) -> str:
        nonlocal had_weights
        had_weights = True
        text = match.group(1).strip()
        tokens.append(WeightedTag(text=text, weight=1.1))
        return text

    work = _DOUBLE_PAREN_RE.sub(repl_double, work)

    def repl_paren(match: re.Match[str]) -> str:
        nonlocal had_weights
        had_weights = True
        text = match.group(1).strip()
        weight_str = match.group(2)
        weight = float(weight_str) if weight_str else 1.1
        tokens.append(WeightedTag(text=text, weight=weight))
        return text

    work = _WEIGHTED_PAREN_RE.sub(repl_paren, work)

    def repl_bracket(match: re.Match[str]) -> str:
        nonlocal had_weights
        had_weights = True
        text = match.group(1).strip()
        tokens.append(WeightedTag(text=text, weight=0.9))
        return text

    work = _BRACKET_RE.sub(repl_bracket, work)
    return work, tokens, had_weights


def normalize_weights(prompt: str) -> NormalizedPrompt:
    """Extract weighted tags and return a clean prompt for registry matching."""
    clean, tokens, had_weights = _strip_outer_weights(prompt.strip())
    clean = re.sub(r"\s*\n\s*", "\n", clean)
    clean = re.sub(r"\s*,\s*", ", ", clean)
    return NormalizedPrompt(tokens=tokens, clean_prompt=clean.strip(), had_weights=had_weights)


def apply_weights_to_tags(tags: list[str], weights: list[WeightedTag]) -> list[str]:
    """Restore (tag:weight) for Illustrious/Pony output."""
    weight_map = {w.text.lower().strip(): w.weight for w in weights}
    out: list[str] = []
    for tag in tags:
        key = tag.lower().strip()
        weight = weight_map.get(key)
        if weight is None or abs(weight - 1.0) < 0.01:
            out.append(tag)
        else:
            out.append(f"({tag}:{weight:g})")
    return out


def format_weighted_prompt(tags: list[str], weights: list[WeightedTag]) -> str:
    return ", ".join(apply_weights_to_tags(tags, weights))
