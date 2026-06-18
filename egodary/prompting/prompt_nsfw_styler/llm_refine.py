"""LLM refinement for NSFW styler (optional Ollama)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from egodary.app import get_llm_settings
from egodary.core.models import PromptState
from egodary.core.pipeline import PromptEngine
from egodary.integrations.ollama import (
    get_cached_health,
    refine_prompt_with_ollama,
    rewrite_prompt_with_ollama,
    user_rewrite_prompt_with_ollama,
)
from egodary.prompting.prompt_analyze.extract_core import CorePrompt
from egodary.prompting.prompt_nsfw_styler.context import collect_mutable_fragments
from egodary.prompting.prompt_nsfw_styler.intensity import NsfwIntensity

LlmMode = Literal["catalog", "rewrite", "user"]


@dataclass
class LlmRefineResult:
    before: str
    after: str
    changed_sections: list[str] = field(default_factory=list)
    used_llm: bool = False
    llm_mode: LlmMode = "catalog"
    llm_error: str | None = None


def llm_refine(
    *,
    before: str,
    intensity: NsfwIntensity,
    model_id: str,
    core: CorePrompt | None = None,
    source_prompt: str | None = None,
    unknown_phrases: list[str] | None = None,
    state: PromptState | None = None,
    engine: PromptEngine | None = None,
    use_llm: bool = True,
    llm_mode: LlmMode = "catalog",
    keep_locked: bool = True,
    user_instruction: str | None = None,
) -> LlmRefineResult:
    settings = get_llm_settings()
    instruction = (user_instruction or "").strip()
    effective_mode: LlmMode = "user" if instruction else llm_mode
    use_llm = use_llm or bool(instruction)

    if not use_llm or not settings.enabled:
        return LlmRefineResult(before=before, after=before, used_llm=False, llm_mode=effective_mode)
    if intensity in ("low",) and effective_mode != "user":
        return LlmRefineResult(before=before, after=before, used_llm=False, llm_mode=effective_mode)

    health = get_cached_health(settings)
    if not health.ok:
        return LlmRefineResult(
            before=before,
            after=before,
            used_llm=False,
            llm_mode=effective_mode,
            llm_error=health.error or "LLM is unavailable",
        )

    source = (source_prompt or before).strip()
    unknown = list(unknown_phrases or [])

    if effective_mode == "user":
        data = user_rewrite_prompt_with_ollama(
            source_prompt=source,
            user_instruction=instruction,
            intensity=intensity,
            model_id=model_id,
            unknown_phrases=unknown,
        )
    elif effective_mode == "rewrite":
        data = rewrite_prompt_with_ollama(
            source_prompt=source,
            intensity=intensity,
            model_id=model_id,
            core=core,
            unknown_phrases=unknown,
            keep_locked=keep_locked,
        )
    else:
        fragments = collect_mutable_fragments(state, core, unknown_phrases=unknown) if state is not None else []
        data = refine_prompt_with_ollama(
            before=before,
            intensity=intensity,
            model_id=model_id,
            core=core,
            mutable_fragments=fragments,
            source_prompt=source,
            assembled_draft=before,
            unknown_phrases=unknown,
            keep_locked=keep_locked,
        )

    if not data:
        return LlmRefineResult(
            before=before,
            after=before,
            used_llm=False,
            llm_mode=effective_mode,
            llm_error="LLM returned no result",
        )

    after = str(data.get("refined_prompt") or before)
    sections = list(data.get("changed_sections") or [])
    return LlmRefineResult(
        before=before,
        after=after,
        changed_sections=sections,
        used_llm=True,
        llm_mode=effective_mode,
    )
