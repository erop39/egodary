"""Prompt Analyze convert pipeline: text/JSON → JSON v1.2 → target model text."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from egodary.core.models import AssembledPrompt, PromptBuckets, PromptState
from egodary.core.pipeline import PromptEngine
from egodary.core.runtime_registry import RuntimeRegistry
from egodary.prompting.prompt_analyze.convert_to_json import (
    prompt_text_to_json,
    state_to_json_prompt,
    try_parse_json_prompt,
)
from egodary.prompting.prompt_analyze.extract_core import CorePrompt
from egodary.prompting.prompt_analyze.input_format import PromptFormat, detect_prompt_format
from egodary.prompting.prompt_analyze.json_schema import split_positive_negative
from egodary.prompting.prompt_analyze.json_to_model import render_json_for_model, render_zimage_turbo_full
from egodary.prompting.prompt_analyze.normalize_weights import NormalizedPrompt, normalize_weights


@dataclass
class ConvertAnalyzeResult:
    detected_format: PromptFormat
    prompt_json: dict[str, Any]
    format: Literal["json", "text"]
    positive: str | None = None
    negative: str | None = None
    model_id: str | None = None
    zit_semantics: dict[str, Any] | None = None
    zit_paragraphs: list[str] = field(default_factory=list)
    used_llm: bool = False


def _json_from_inputs(
    *,
    prompt: str | None,
    state: PromptState | None,
    core: CorePrompt | None,
    source_model: str,
    model_target: str,
    engine: PromptEngine,
    registry: RuntimeRegistry | None,
    inline_negative: str | None = None,
) -> dict[str, Any]:
    existing = try_parse_json_prompt(prompt or "")
    if existing is not None:
        payload = existing.copy()
        payload["model_target"] = model_target
        return payload

    if state is not None:
        return state_to_json_prompt(
            state=state,
            engine=engine,
            model_target=model_target,
            negative_text=inline_negative,
        )

    if core is not None:
        return state_to_json_prompt(
            state=core.state,
            engine=engine,
            model_target=model_target,
            negative_text=inline_negative,
        )

    if prompt is not None:
        return prompt_text_to_json(
            prompt=prompt,
            source_model=source_model,
            model_target=model_target,
            engine=engine,
            registry=registry,
        )

    raise ValueError("prompt, state, core, or JSON prompt is required")


def convert_analyze(
    *,
    prompt: str | None = None,
    state: PromptState | None = None,
    core: CorePrompt | None = None,
    source_model: str = "illustrious",
    target_model: str = "illustrious",
    engine: PromptEngine,
    registry: RuntimeRegistry | None = None,
    use_llm: bool = False,
) -> ConvertAnalyzeResult:
    """Unified convert: input → JSON v1.2 → target (json | illustrious | anima | zimage_turbo)."""
    work_prompt = prompt
    inline_negative: str | None = None
    detected = detect_prompt_format(work_prompt or "")

    if work_prompt and detected != "json":
        positive_text, inline_negative = split_positive_negative(work_prompt)
        if positive_text != work_prompt:
            work_prompt = positive_text
            detected = detect_prompt_format(work_prompt)

    model_target = source_model if target_model == "json" else target_model
    prompt_json = _json_from_inputs(
        prompt=work_prompt,
        state=state,
        core=core,
        source_model=source_model,
        model_target=model_target,
        engine=engine,
        registry=registry,
        inline_negative=inline_negative,
    )

    if target_model == "json":
        return ConvertAnalyzeResult(
            detected_format=detected,
            prompt_json=prompt_json,
            format="json",
            model_id=model_target,
        )

    if target_model == "zimage_turbo":
        zit_result = render_zimage_turbo_full(prompt_json, use_llm=use_llm)
        return ConvertAnalyzeResult(
            detected_format=detected,
            prompt_json=prompt_json,
            format="text",
            positive=zit_result.text,
            negative=None,
            model_id=target_model,
            zit_semantics=zit_result.semantics.to_dict(),
            zit_paragraphs=zit_result.paragraphs,
            used_llm=zit_result.used_llm,
        )

    positive, negative = render_json_for_model(prompt_json, target_model, engine)
    return ConvertAnalyzeResult(
        detected_format=detected,
        prompt_json=prompt_json,
        format="text",
        positive=positive,
        negative=negative or None,
        model_id=target_model,
    )


def convert_to_model(
    *,
    prompt: str | None = None,
    state: PromptState | None = None,
    core: CorePrompt | None = None,
    source_model: str = "illustrious",
    target_model: str = "illustrious",
    engine: PromptEngine,
    registry: RuntimeRegistry | None = None,
) -> tuple[AssembledPrompt, PromptFormat, NormalizedPrompt | None]:
    """Backward-compatible wrapper around JSON-first convert_analyze pipeline."""
    normalized: NormalizedPrompt | None = None
    if prompt is not None and detect_prompt_format(prompt) != "json":
        normalized = normalize_weights(prompt)

    result = convert_analyze(
        prompt=prompt,
        state=state,
        core=core,
        source_model=source_model,
        target_model=target_model,
        engine=engine,
        registry=registry,
    )
    assembled = AssembledPrompt(
        positive=result.positive or "",
        negative=result.negative,
        buckets=PromptBuckets(),
        model_id=result.model_id or target_model,
    )
    return assembled, result.detected_format, normalized
