"""Merge classified tags into the runtime registry overlay."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from egodary.core.runtime_registry import AddItemResult, ConflictPolicy, OverlaySource, RuntimeRegistry
from egodary.prompting.prompt_import.classify_new_tags import ClassifiedTag
from egodary.prompting.prompt_import.parse_imported_prompt import parse_imported_prompt


@dataclass
class MergeReport:
    added: list[AddItemResult] = field(default_factory=list)
    skipped: list[AddItemResult] = field(default_factory=list)
    reparsed_unknown_count: int = 0


def _default_conflict_policy() -> ConflictPolicy:
    raw = os.environ.get("EGODARY_OVERLAY_CONFLICT_POLICY", "rename")
    if raw in ("skip", "overwrite", "rename"):
        return raw  # type: ignore[return-value]
    return "rename"


def merge_to_registry(
    classified: list[ClassifiedTag],
    registry: RuntimeRegistry,
    *,
    source: OverlaySource = "import",
    on_conflict: ConflictPolicy | None = None,
    persist: bool = False,
    reprompt: str | None = None,
    model_id: str = "illustrious",
    allow_conflicts: bool = False,
) -> MergeReport:
    policy = on_conflict or _default_conflict_policy()
    report = MergeReport()

    for tag in classified:
        if tag.action != "new" or tag.item is None:
            continue
        if tag.conflict_status == "hard_conflict" and not allow_conflicts:
            report.skipped.append(
                AddItemResult(
                    item_id=tag.item.id,
                    category_id=tag.category_id,
                    action="skipped",
                    previous_id=tag.item.id,
                )
            )
            continue
        result = registry.add_item(
            tag.category_id,
            tag.item,
            source=source,
            on_conflict=policy,
            original_phrase=tag.phrase,
        )
        if result.action == "skipped":
            report.skipped.append(result)
        else:
            report.added.append(result)

    if persist:
        from egodary.persistence.schema import save_runtime_tag_items

        save_runtime_tag_items(registry)

    if reprompt:
        reparsed = parse_imported_prompt(reprompt, model_id, registry)
        report.reparsed_unknown_count = len(reparsed.unknown)

    return report
