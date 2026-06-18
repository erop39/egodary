"""NSFW styler intensity presets."""

from __future__ import annotations

from typing import Literal

NsfwIntensity = Literal["low", "medium", "high", "extreme"]

INTENSITY_LEWDNESS: dict[NsfwIntensity, int] = {
    "low": 3,
    "medium": 5,
    "high": 8,
    "extreme": 10,
}


def intensity_to_lewdness(intensity: NsfwIntensity) -> int:
    return INTENSITY_LEWDNESS[intensity]
