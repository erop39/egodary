"""NSFW styler package exports.

Keep this module lightweight to avoid circular imports:
`integrations.ollama` imports `context`, while `llm_refine` imports `integrations.ollama`.
"""

from __future__ import annotations

from egodary.prompting.prompt_nsfw_styler.context import collect_identity_buckets, collect_mutable_fragments
from egodary.prompting.prompt_nsfw_styler.intensity import NsfwIntensity, intensity_to_lewdness
from egodary.prompting.prompt_nsfw_styler.rule_based_enhance import rule_based_enhance

__all__ = [
    "NsfwIntensity",
    "collect_identity_buckets",
    "collect_mutable_fragments",
    "intensity_to_lewdness",
    "rule_based_enhance",
    "llm_refine",
    "LlmRefineResult",
]


def __getattr__(name: str):
    if name in {"llm_refine", "LlmRefineResult"}:
        import importlib

        llm_refine_module = importlib.import_module("egodary.prompting.prompt_nsfw_styler.llm_refine")
        if name == "llm_refine":
            # Expose the submodule to preserve dotted monkeypatch paths.
            return llm_refine_module
        return llm_refine_module.LlmRefineResult
    raise AttributeError(name)
