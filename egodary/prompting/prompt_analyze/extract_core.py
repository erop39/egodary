"""Extract locked core layers from a prompt."""

from __future__ import annotations

from dataclasses import dataclass, field

from egodary.core.importer import import_prompt_with_report
from egodary.core.models import PromptState
from egodary.core.runtime_registry import RuntimeRegistry
from egodary.prompting.prompt_analyze.normalize_weights import normalize_weights

LOCKED_PREFIXES = (
    "character.",
    "face.",
    "appearance.hair",
    "appearance.hair_color",
    "style.",
    "scene.",
    "environment.location",
)

KEY_TAG_PREFIXES = (
    "outfit.",
    "pose",
    "appearance.",
    "camera.",
    "lighting.",
)


@dataclass
class CorePrompt:
    state: PromptState
    locked_paths: set[str] = field(default_factory=set)
    locked_values: dict[str, str] = field(default_factory=dict)
    layers: dict[str, list[str]] = field(default_factory=dict)

    def locked_buckets(self) -> list[dict[str, str]]:
        return [
            {
                "path": path,
                "value": self.locked_values.get(path, ""),
                "item_id": self.locked_values.get(f"{path}__id", ""),
            }
            for path in sorted(self.locked_paths)
        ]


def _is_locked_path(field_path: str) -> bool:
    if field_path == "pose":
        return False
    return any(field_path.startswith(prefix) or field_path == prefix.rstrip(".") for prefix in LOCKED_PREFIXES)


def _layer_for_path(field_path: str) -> str:
    if field_path.startswith("character.") or field_path.startswith("face.") or field_path.startswith("appearance.hair"):
        return "character"
    if field_path.startswith("scene.") or field_path.startswith("environment."):
        return "scene"
    if field_path.startswith("style."):
        return "style"
    return "key_tags"


def extract_core(
    prompt: str,
    model_id: str = "illustrious",
    registry: RuntimeRegistry | None = None,
) -> CorePrompt:
    normalized = normalize_weights(prompt)
    result = import_prompt_with_report(normalized.clean_prompt or prompt, model_id, registry)
    locked_paths: set[str] = set()
    locked_values: dict[str, str] = {}
    layers: dict[str, list[str]] = {
        "character": [],
        "scene": [],
        "style": [],
        "key_tags": [],
    }

    for match in result.matched:
        path = match.field_path
        layer = _layer_for_path(path)
        label = f"{match.label} ({match.matched_phrase})"
        layers.setdefault(layer, []).append(label)
        if _is_locked_path(path):
            locked_paths.add(path)
            locked_values[path] = match.matched_phrase
            locked_values[f"{path}__id"] = match.item_id

    return CorePrompt(
        state=result.state,
        locked_paths=locked_paths,
        locked_values=locked_values,
        layers=layers,
    )
