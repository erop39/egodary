"""Import prompt text back to PromptState using the tag registry."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from egodary.core.models import PromptState, TagItem
from egodary.core.registry import TagRegistry
from egodary.core.runtime_registry import RuntimeRegistry

RegistryLike = TagRegistry | RuntimeRegistry

SKIP_PHRASES = frozenset(
    {
        "styled outfit",
        "styled accessory",
        "face makeup",
        "detailed hairstyle",
        "dynamic pose",
        "clothing detail",
        "cinematic framing",
        "cinematic lighting",
        "detailed face",
        "wearing",
        "with",
        "and",
    }
)

SKIP_UNKNOWN = frozenset(
    {
        "1girl",
        "2girls",
        "solo",
        "best quality",
        "masterpiece",
        "high quality",
        "anime style",
        "clean anatomy",
        "coherent composition",
        "score_7",
        "score_8_up",
        "score_7_up",
        "score_9",
        "score_8",
    }
)

MULTI_CATEGORIES = frozenset(
    {
        "appearance.makeup",
        "appearance.accessories",
        "environment.modifiers",
        "style.quality",
        "style.aesthetic",
        "style.technique",
        "fetish.elements",
        "character.body_details",
    }
)

POSE_CATEGORIES = frozenset({"pose.solo", "pose.couple"})


@dataclass
class ImportMatch:
    category_id: str
    item_id: str
    label: str
    matched_phrase: str
    field_path: str

    def to_dict(self) -> dict:
        return {
            "category_id": self.category_id,
            "item_id": self.item_id,
            "label": self.label,
            "matched_phrase": self.matched_phrase,
            "field_path": self.field_path,
        }


@dataclass
class ImportResult:
    state: PromptState
    matched: list[ImportMatch] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)
    touched: list[str] = field(default_factory=list)

    def to_report(self) -> dict:
        return {
            "matched": [m.to_dict() for m in self.matched],
            "unknown": self.unknown,
            "touched": self.touched,
            "matched_count": len(self.matched),
            "unknown_count": len(self.unknown),
        }


@dataclass
class _Candidate:
    category_id: str
    item_id: str
    label: str
    phrase: str
    phrase_norm: str
    field_path: str


def import_prompt_to_state(
    prompt: str,
    model_id: str = "illustrious",
    registry: RegistryLike | None = None,
) -> PromptState:
    """Backward-compatible helper — returns only the parsed state."""
    return import_prompt_with_report(prompt, model_id, registry).state


def import_prompt_with_report(
    prompt: str,
    model_id: str = "illustrious",
    registry: RegistryLike | None = None,
) -> ImportResult:
    if registry is None:
        from egodary.bootstrap import build_app

        registry, _ = build_app()

    candidates = _build_candidates(registry, model_id)
    matches = _find_matches(prompt, candidates)
    state, matched, touched = _apply_matches(prompt, model_id, matches)
    unknown = _extract_unknown(prompt, matched)
    return ImportResult(state=state, matched=matched, unknown=unknown, touched=sorted(touched))


def _resolve_field_path(category_id: str) -> str | None:
    if category_id in POSE_CATEGORIES:
        return "pose"
    if category_id in MULTI_CATEGORIES:
        section, fld = category_id.split(".", 1)
        return f"{section}.{fld}"
    if category_id == "outfit.clothing_condition":
        return None
    parts = category_id.split(".", 1)
    if len(parts) != 2:
        return None
    section, fld = parts
    if section in {"outfit", "face", "camera", "lighting", "scene", "environment", "style", "appearance", "character"}:
        return f"{section}.{fld}"
    return None


def _tag_text_for_model(item: TagItem, model_id: str) -> str:
    if model_id in item.tags:
        return item.tags[model_id]
    if model_id == "zimage_turbo" and "zimage" in item.tags:
        return item.tags["zimage"]
    return item.tags.get("illustrious") or item.tags.get("default") or next(iter(item.tags.values()), "")


def _phrases_for_item(category_id: str, item: TagItem, model_id: str) -> list[str]:
    phrases: list[str] = []
    tag_text = _tag_text_for_model(item, model_id)
    if tag_text:
        phrases.append(tag_text.strip())
        for part in tag_text.split(","):
            cleaned = part.strip()
            if cleaned and cleaned.lower() not in SKIP_PHRASES and len(cleaned) >= 3:
                phrases.append(cleaned)
    label = item.label.strip()
    if label and len(label) >= 3:
        phrases.append(label)
    slug_words = item.id.replace("_", " ").strip()
    if slug_words and slug_words != label.lower():
        phrases.append(slug_words)
    # de-duplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for phrase in phrases:
        key = phrase.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(phrase)
    _ = category_id
    return unique


def _build_candidates(registry: RegistryLike, model_id: str) -> list[_Candidate]:
    result: list[_Candidate] = []
    for category_id in registry.category_ids():
        field_path = _resolve_field_path(category_id)
        if not field_path:
            continue
        category = registry.get_category(category_id)
        if not category:
            continue
        for item in category.items:
            for phrase in _phrases_for_item(category_id, item, model_id):
                result.append(
                    _Candidate(
                        category_id=category_id,
                        item_id=item.id,
                        label=item.label,
                        phrase=phrase,
                        phrase_norm=phrase.lower(),
                        field_path=field_path,
                    )
                )
    return result


def _find_matches(prompt: str, candidates: list[_Candidate]) -> list[_Candidate]:
    text = prompt.lower()
    consumed = [False] * len(text)
    matched: list[_Candidate] = []
    seen_items: set[tuple[str, str]] = set()

    for cand in sorted(candidates, key=lambda c: len(c.phrase_norm), reverse=True):
        if len(cand.phrase_norm) < 3:
            continue
        key = (cand.category_id, cand.item_id)
        if key in seen_items:
            continue
        idx = text.find(cand.phrase_norm)
        if idx == -1:
            continue
        end = idx + len(cand.phrase_norm)
        if any(consumed[idx:end]):
            continue
        for i in range(idx, end):
            consumed[i] = True
        matched.append(cand)
        seen_items.add(key)
    return matched


def _set_path(state: PromptState, field_path: str, item_id: str, *, multi: bool) -> None:
    section, fld = field_path.split(".", 1)
    container = getattr(state, section)
    if multi:
        values: list[str] = getattr(container, fld)
        if item_id not in values:
            values.append(item_id)
    else:
        setattr(container, fld, item_id)


def _apply_matches(
    prompt: str,
    model_id: str,
    matches: list[_Candidate],
) -> tuple[PromptState, list[ImportMatch], set[str]]:
    state = PromptState(model_id=model_id)
    touched: set[str] = set()
    report: list[ImportMatch] = []
    single_best: dict[str, _Candidate] = {}

    for cand in matches:
        if cand.field_path == "pose":
            state.pose = cand.item_id
            touched.add("pose")
            report.append(
                ImportMatch(
                    category_id=cand.category_id,
                    item_id=cand.item_id,
                    label=cand.label,
                    matched_phrase=cand.phrase,
                    field_path="pose",
                )
            )
            continue

        is_multi = cand.category_id in MULTI_CATEGORIES
        if is_multi:
            _set_path(state, cand.field_path, cand.item_id, multi=True)
            touched.add(cand.field_path)
            report.append(
                ImportMatch(
                    category_id=cand.category_id,
                    item_id=cand.item_id,
                    label=cand.label,
                    matched_phrase=cand.phrase,
                    field_path=cand.field_path,
                )
            )
            continue

        prev = single_best.get(cand.field_path)
        if prev is None or len(cand.phrase_norm) > len(prev.phrase_norm):
            single_best[cand.field_path] = cand

    for field_path, cand in single_best.items():
        _set_path(state, field_path, cand.item_id, multi=False)
        touched.add(field_path)
        report.append(
            ImportMatch(
                category_id=cand.category_id,
                item_id=cand.item_id,
                label=cand.label,
                matched_phrase=cand.phrase,
                field_path=field_path,
            )
        )

    if any(path.startswith("style.") for path in touched):
        state.style.enabled = True
        touched.add("style.enabled")

    text_low = prompt.lower()
    if "2girls" in text_low or "2 girls" in text_low or "two girls" in text_low:
        state.group_mode = True
        touched.add("group_mode")

    age_match = re.search(r"\b(\d{1,2})\s*years?\s*old\b", text_low)
    if age_match:
        age = int(age_match.group(1))
        if age <= 20:
            state.character.age_appearance = "18_20"
        elif age <= 25:
            state.character.age_appearance = "21_25"
        elif age <= 30:
            state.character.age_appearance = "26_30"
        elif age <= 35:
            state.character.age_appearance = "31_35"
        elif age <= 40:
            state.character.age_appearance = "36_40"
        else:
            state.character.age_appearance = "mature_beauty_35_45"
        touched.add("character.age_appearance")

    return state, report, touched


def _extract_unknown(prompt: str, matched: list[ImportMatch]) -> list[str]:
    matched_phrases = {m.matched_phrase.lower().strip() for m in matched}
    unknown: list[str] = []
    seen: set[str] = set()

    for segment in re.split(r"[\n,]+", prompt):
        token = segment.strip()
        if not token or len(token) < 2:
            continue
        token_low = token.lower()
        if token_low in SKIP_UNKNOWN:
            continue
        if re.match(r"^score[_\s]?\d", token_low):
            continue
        if any(token_low in phrase or phrase in token_low for phrase in matched_phrases):
            continue
        if token_low in seen:
            continue
        seen.add(token_low)
        unknown.append(token)
    return unknown
