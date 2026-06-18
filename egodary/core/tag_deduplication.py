"""Tag deduplication service for manual add/import flows."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Literal

from egodary.core.models import TagItem

MatchType = Literal["exact_name", "alias_collision", "fuzzy_name"]


@dataclass
class DedupeMatch:
    match_type: MatchType
    item_id: str
    label: str
    score: float
    reason: str


class TagDeduplicationService:
    """Category-scoped deduplication using exact, alias and fuzzy checks."""

    def __init__(self, *, fuzzy_threshold: float = 0.9) -> None:
        self._fuzzy_threshold = max(0.5, min(1.0, float(fuzzy_threshold)))

    @staticmethod
    def normalize(value: str) -> str:
        text = re.sub(r"\s+", " ", (value or "").strip().lower())
        return text

    def find_matches(
        self,
        *,
        phrase: str,
        category_id: str,
        items: list[TagItem],
    ) -> list[DedupeMatch]:
        normalized_phrase = self.normalize(phrase)
        if not normalized_phrase:
            return []

        matches: list[DedupeMatch] = []
        for item in items:
            meta = item.meta or {}
            if meta.get("is_active") is False:
                continue

            item_norm = self.normalize(str(meta.get("normalized_name") or item.label))
            if item_norm == normalized_phrase:
                matches.append(
                    DedupeMatch(
                        match_type="exact_name",
                        item_id=item.id,
                        label=item.label,
                        score=1.0,
                        reason=f"Exact name duplicate in {category_id}",
                    )
                )
                continue

            aliases = [self.normalize(str(alias)) for alias in (meta.get("aliases") or []) if str(alias).strip()]
            if normalized_phrase in aliases:
                matches.append(
                    DedupeMatch(
                        match_type="alias_collision",
                        item_id=item.id,
                        label=item.label,
                        score=1.0,
                        reason=f"Alias collision in {category_id}",
                    )
                )
                continue

            fuzzy_score = SequenceMatcher(None, normalized_phrase, item_norm).ratio()
            if fuzzy_score >= self._fuzzy_threshold:
                matches.append(
                    DedupeMatch(
                        match_type="fuzzy_name",
                        item_id=item.id,
                        label=item.label,
                        score=round(fuzzy_score, 3),
                        reason=f"Possible duplicate by fuzzy score >= {self._fuzzy_threshold}",
                    )
                )

        return sorted(matches, key=lambda m: m.score, reverse=True)
