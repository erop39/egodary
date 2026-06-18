"""Strict LLM refinement for Z-Image Turbo convert v1.1."""

from __future__ import annotations

import re
from dataclasses import dataclass

from egodary.app import get_llm_settings
from egodary.integrations.ollama import get_cached_health, refine_zit_prompt_with_ollama
from egodary.prompting.prompt_analyze.zit_renderer import ZitRenderResult

FORBIDDEN_OUTPUT_PATTERNS = re.compile(
    r"\b(masterpiece|best quality|highres|absurdres|1girl|2girls|1boy|solo|score_\d+)\b",
    re.I,
)

PARAGRAPH_ORDER = [
    "subject_pose_view",
    "appearance",
    "outfit",
    "scene",
    "lighting",
    "camera",
    "materials",
    "render_line",
]


@dataclass
class ZitLlmRefineResult:
    result: ZitRenderResult
    violations: list[str]


def _has_violations(text: str) -> list[str]:
    violations: list[str] = []
    for match in FORBIDDEN_OUTPUT_PATTERNS.finditer(text):
        violations.append(match.group(0).lower())
    return violations


def zit_llm_refine(
    draft: ZitRenderResult,
    *,
    use_llm: bool = True,
) -> ZitLlmRefineResult:
    if not use_llm:
        return ZitLlmRefineResult(result=draft, violations=[])

    settings = get_llm_settings()
    if not settings.enabled:
        return ZitLlmRefineResult(result=draft, violations=[])

    health = get_cached_health(settings)
    if not health.ok:
        return ZitLlmRefineResult(result=draft, violations=[])

    data = refine_zit_prompt_with_ollama(
        draft_prompt=draft.text,
        semantics=draft.semantics.to_dict(),
        paragraph_order=PARAGRAPH_ORDER,
    )
    if not data:
        return ZitLlmRefineResult(result=draft, violations=[])

    refined = str(data.get("refined_prompt") or "").strip()
    llm_violations = list(data.get("violations") or [])
    if not refined:
        return ZitLlmRefineResult(result=draft, violations=llm_violations)

    detected = _has_violations(refined)
    if detected:
        return ZitLlmRefineResult(result=draft, violations=detected + llm_violations)

    paragraphs = [p.strip() for p in refined.split("\n\n") if p.strip()]
    refined_result = ZitRenderResult(
        text=refined,
        semantics=draft.semantics,
        paragraphs=paragraphs or draft.paragraphs,
        used_llm=True,
        draft_text=draft.text,
    )
    return ZitLlmRefineResult(result=refined_result, violations=llm_violations)
