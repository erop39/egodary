"""Parse imported prompts against the runtime registry."""

from __future__ import annotations

from dataclasses import dataclass, field

from egodary.core.importer import ImportResult, import_prompt_with_report
from egodary.core.runtime_registry import RuntimeRegistry
from egodary.prompting.prompt_analyze.normalize_weights import WeightedTag, normalize_weights


@dataclass
class ImportParseResult:
    state: ImportResult
    normalized_clean: str
    weighted_tokens: list[WeightedTag] = field(default_factory=list)
    had_weights: bool = False

    @property
    def matched(self):
        return self.state.matched

    @property
    def unknown(self):
        return self.state.unknown

    @property
    def touched(self):
        return self.state.touched


def parse_imported_prompt(
    prompt: str,
    model_id: str = "illustrious",
    registry: RuntimeRegistry | None = None,
) -> ImportParseResult:
    normalized = normalize_weights(prompt)
    clean = normalized.clean_prompt or prompt.strip()
    result = import_prompt_with_report(clean, model_id, registry)
    return ImportParseResult(
        state=result,
        normalized_clean=clean,
        weighted_tokens=normalized.tokens,
        had_weights=normalized.had_weights,
    )
