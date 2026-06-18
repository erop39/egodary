"""Classify unknown prompt phrases into registry categories."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Literal

from egodary.app import get_llm_settings
from egodary.core.models import TagItem
from egodary.core.runtime_registry import RuntimeRegistry
from egodary.core.tag_deduplication import TagDeduplicationService
from egodary.integrations.ollama import get_cached_health
from egodary.prompting.prompt_analyze.extract_core import CorePrompt

ClassifyAction = Literal["new", "merge_into_existing", "skip"]

_KEYWORD_RULES: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"\b(dress|gown|skirt)\b", re.I), "outfit.dress", "imported"),
    (re.compile(r"\b(shirt|top|blouse|bra)\b", re.I), "outfit.top", "imported"),
    (re.compile(r"\b(pants|shorts|panties|bottom)\b", re.I), "outfit.bottom", "imported"),
    (re.compile(r"\b(hair|ponytail|braid)\b", re.I), "appearance.hair", "imported"),
    (re.compile(r"\b(eye|eyes)\b", re.I), "face.eyes", "imported"),
    (re.compile(r"\b(pose|standing|sitting|lying)\b", re.I), "pose.solo", "imported"),
    (re.compile(r"\b(camera|angle|shot|framing)\b", re.I), "camera.angle", "imported"),
    (re.compile(r"\b(light|lighting|shadow)\b", re.I), "lighting.light_type", "imported"),
    (re.compile(r"\b(night|day|sunset|morning)\b", re.I), "scene.time_of_day", "imported"),
    (re.compile(r"\b(anime|style|artist)\b", re.I), "style.art_style", "imported"),
]

_CATEGORY_KEYWORDS: dict[str, str] = {
    "dress": "outfit.dress",
    "top": "outfit.top",
    "bottom": "outfit.bottom",
    "hair": "appearance.hair",
    "eyes": "face.eyes",
}


@dataclass
class DedupeResult:
    phrase: str
    action: ClassifyAction
    field_path: str | None = None
    note: str = ""


@dataclass
class ClassifiedTag:
    phrase: str
    action: ClassifyAction = "new"
    category_id: str = "prompting.imported"
    subgroup: str = "unclassified"
    subcategory_id: str = "unclassified"
    label: str = ""
    merge_path: str | None = None
    conflict_status: str = "none"
    item: TagItem | None = None
    variants: dict[str, str] = field(default_factory=dict)


def _normalize_phrase(phrase: str) -> str:
    return re.sub(r"\s+", " ", phrase.lower().strip())


def _guess_category(phrase: str) -> tuple[str, str]:
    for pattern, category_id, subgroup in _KEYWORD_RULES:
        if pattern.search(phrase):
            return category_id, subgroup
    return "prompting.imported", "unclassified"


def _dedupe_against_core(phrase: str, core: CorePrompt | None) -> DedupeResult | None:
    if core is None:
        return None
    norm = _normalize_phrase(phrase)
    for path, value in core.locked_values.items():
        if path.endswith("__id"):
            continue
        val_norm = _normalize_phrase(value)
        if not val_norm:
            continue
        if norm == val_norm or norm in val_norm or val_norm in norm:
            for keyword, cat_path in _CATEGORY_KEYWORDS.items():
                if keyword in path or keyword in norm:
                    if path.startswith("outfit.") or path.startswith("face.") or path.startswith("appearance."):
                        return DedupeResult(
                            phrase=phrase,
                            action="merge_into_existing",
                            field_path=path,
                            note="modifier of existing locked bucket",
                        )
            if norm in val_norm or val_norm in norm:
                return DedupeResult(
                    phrase=phrase,
                    action="merge_into_existing",
                    field_path=path.split("__")[0] if "__" in path else path,
                    note="overlaps locked value",
                )
    return None


def _make_item_id(phrase: str) -> str:
    digest = hashlib.sha256(phrase.encode()).hexdigest()[:10]
    slug = re.sub(r"[^a-z0-9]+", "_", phrase.lower().strip())[:32].strip("_")
    return f"imported_{slug}_{digest}" if slug else f"imported_{digest}"


def _build_tag_item(phrase: str, category_id: str, subgroup: str, label: str | None = None) -> TagItem:
    clean_label = label or phrase.strip().title()
    variants = {
        "illustrious": phrase.strip(),
        "anima": phrase.strip(),
        "zimage_turbo": phrase.strip(),
        "pony": phrase.strip(),
    }
    return TagItem(
        id=_make_item_id(phrase),
        label=clean_label,
        tags=variants,
        meta={
            "subgroup": subgroup,
            "subcategory_id": subgroup,
            "source": "import",
            "normalized_name": clean_label.strip().lower(),
            "aliases": [],
            "is_active": True,
        },
    )


def classify_new_tags(
    unknown: list[str],
    core: CorePrompt | None = None,
    registry: RuntimeRegistry | None = None,
    *,
    use_ollama: bool = False,
) -> tuple[list[DedupeResult], list[ClassifiedTag]]:
    """Rules-based classification with dedupe against CorePrompt. Ollama optional."""
    deduped: list[DedupeResult] = []
    classified: list[ClassifiedTag] = []
    remaining: list[str] = []
    dedupe_service = TagDeduplicationService()

    for phrase in unknown:
        dup = _dedupe_against_core(phrase, core)
        if dup:
            deduped.append(dup)
            continue
        remaining.append(phrase)

    if use_ollama and remaining:
        settings = get_llm_settings()
        if not settings.enabled:
            use_ollama = False
        else:
            health = get_cached_health(settings)
            if not health.ok:
                use_ollama = False
    if use_ollama and remaining:
        from egodary.integrations.ollama import classify_phrases_with_ollama

        ollama_results = classify_phrases_with_ollama(remaining, core)
        for entry in ollama_results:
            action = entry.get("action", "new")
            if action in ("skip", "merge_into_existing"):
                deduped.append(
                    DedupeResult(
                        phrase=entry.get("phrase", ""),
                        action=action,
                        field_path=entry.get("merge_path"),
                        note="ollama dedupe",
                    )
                )
                continue
            phrase = entry.get("phrase", "")
            category_id = entry.get("category_id", "prompting.imported")
            subcategory_id = entry.get("subcategory_id") or entry.get("subgroup") or "imported"
            variants = entry.get("variants") or {k: phrase for k in ("illustrious", "anima", "zimage_turbo", "pony")}
            item = TagItem(
                id=_make_item_id(phrase),
                label=entry.get("label", phrase.title()),
                tags=variants,
                meta={
                    "subgroup": subcategory_id,
                    "subcategory_id": subcategory_id,
                    "source": "import",
                    "normalized_name": phrase.strip().lower(),
                    "aliases": [],
                    "is_active": True,
                },
            )
            classified.append(
                ClassifiedTag(
                    phrase=phrase,
                    action="new",
                    category_id=category_id,
                    subgroup=subcategory_id,
                    subcategory_id=subcategory_id,
                    label=item.label,
                    conflict_status=str(entry.get("conflict_status") or "none"),
                    item=item,
                    variants=variants,
                )
            )
        classified_phrases = {c.phrase for c in classified}
        remaining = [p for p in remaining if p not in classified_phrases]

    for phrase in remaining:
        category_id, subgroup = _guess_category(phrase)
        item = _build_tag_item(phrase, category_id, subgroup)
        category = registry.get_category(category_id) if registry is not None else None
        conflict_status = "none"
        if category is not None:
            matches = dedupe_service.find_matches(phrase=item.label, category_id=category_id, items=category.items)
            if any(m.match_type in {"exact_name", "alias_collision"} for m in matches):
                conflict_status = "hard_conflict"
            elif matches:
                conflict_status = "possible_conflict"
        classified.append(
            ClassifiedTag(
                phrase=phrase,
                action="new",
                category_id=category_id,
                subgroup=subgroup,
                subcategory_id=subgroup,
                label=item.label,
                conflict_status=conflict_status,
                item=item,
                variants=dict(item.tags),
            )
        )

    return deduped, classified
