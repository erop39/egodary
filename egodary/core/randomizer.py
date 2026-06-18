"""Prompt randomizer and NSFW rulebook checks."""

from __future__ import annotations

import random

from egodary.core.models import PromptState
from egodary.core.scoring import PROMPT_RULEBOOK_MIN_SCORE

NSFW_AXES = ("clothing", "pose", "activity", "camera")

GOD_MODE_BUNDLES = {
    "religious_luxury": {"season": "winter", "weather": "clear_sky", "camera_angle": "low_angle"},
    "cyber_noir": {"season": "autumn", "weather": "fog", "camera_angle": "dutch_angle"},
    "idol_stage": {"season": "summer", "weather": "clear_sky", "camera_angle": "eye_level"},
}


def smart_randomize(state: PromptState) -> PromptState:
    if not state.scene.time:
        state.scene.time = random.choice(["morning", "sunset", "night"])
    if not state.scene.weather:
        state.scene.weather = random.choice(["clear_sky", "cloudy", "fog"])
    if not state.scene.season:
        state.scene.season = random.choice(["spring", "summer", "autumn", "winter"])
    if not state.camera.angle:
        state.camera.angle = random.choice(["eye_level", "low_angle", "high_angle"])
    return state


def apply_god_mode_bundle(state: PromptState, bundle_id: str) -> PromptState:
    payload = GOD_MODE_BUNDLES.get(bundle_id)
    if not payload:
        return state
    state.god_mode_bundle = bundle_id
    state.scene.season = payload["season"]
    state.scene.weather = payload["weather"]
    state.camera.angle = payload["camera_angle"]
    return state


def evaluate_rulebook(metrics: dict[str, int]) -> tuple[int, bool]:
    """Metrics must contain 7 scalar checks from 0..10."""
    score = sum(metrics.values()) // max(len(metrics), 1)
    return score, score >= PROMPT_RULEBOOK_MIN_SCORE

