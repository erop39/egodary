"""In-memory overlay on top of the static TagRegistry."""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from egodary.core.models import ConflictGroup, TagCategory, TagItem
from egodary.core.registry import TagRegistry

logger = logging.getLogger(__name__)

OverlaySource = Literal["import", "user", "manual"]
ConflictPolicy = Literal["skip", "overwrite", "rename"]

VARIANT_KEYS = ("illustrious", "anima", "zimage_turbo", "pony")


@dataclass
class OverlayItemMeta:
    source: OverlaySource
    added_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    original_phrase: str | None = None


@dataclass
class AddItemResult:
    item_id: str
    category_id: str
    action: Literal["added", "skipped", "overwritten", "renamed"]
    previous_id: str | None = None


@dataclass
class _OverlayEntry:
    item: TagItem
    meta: OverlayItemMeta


class RuntimeRegistry:
    """TagRegistry wrapper merging runtime overlay items into category lookups."""

    def __init__(self, base: TagRegistry) -> None:
        self._base = base
        self._overlay: dict[str, dict[str, _OverlayEntry]] = {}

    @property
    def base(self) -> TagRegistry:
        return self._base

    def set_base(self, base: TagRegistry) -> None:
        """Replace underlying registry after content-pack reload."""
        self._base = base

    def category_ids(self) -> list[str]:
        ids = set(self._base.category_ids())
        ids.update(self._overlay.keys())
        return sorted(ids)

    def all_categories(self) -> list[TagCategory]:
        return [self.get_category(cid) for cid in self.category_ids() if self.get_category(cid)]

    def conflict_groups(self) -> list[ConflictGroup]:
        return self._base.conflict_groups()

    @property
    def conflicts(self) -> list[ConflictGroup]:
        return self.conflict_groups()

    def source_of(self, category_id: str) -> str | None:
        if category_id in self._overlay:
            return "runtime_overlay"
        return self._base.source_of(category_id)

    def _overlay_items_for(self, category_id: str) -> list[TagItem]:
        bucket = self._overlay.get(category_id)
        if not bucket:
            return []
        return [entry.item for entry in bucket.values()]

    @staticmethod
    def _is_active(item: TagItem) -> bool:
        meta = item.meta or {}
        return meta.get("is_active") is not False

    def get_category(self, category_id: str) -> TagCategory | None:
        base_cat = self._base.get_category(category_id)
        overlay_items = self._overlay_items_for(category_id)
        if base_cat is None and not overlay_items:
            return None
        active_overlay = [item for item in overlay_items if self._is_active(item)]
        if base_cat is None:
            return TagCategory(id=category_id, title=category_id, items=list(active_overlay))
        if not active_overlay:
            return base_cat
        merged = copy.deepcopy(base_cat)
        merged.items = list(base_cat.items) + list(active_overlay)
        return merged

    def _resolve_tag_from_item(self, item: TagItem, model_id: str, category_id: str, item_id: str) -> str | None:
        if model_id == "pony" and "pony" not in item.tags and "illustrious" in item.tags:
            logger.debug(
                "pony variant missing for %s/%s, fallback to illustrious",
                category_id,
                item_id,
            )
        for key in (model_id, "illustrious", "anima", "default"):
            if key in item.tags:
                return item.tags[key]
            if key == "zimage_turbo" and "zimage" in item.tags:
                return item.tags["zimage"]
        if "zimage" in item.tags and model_id == "zimage_turbo":
            return item.tags["zimage"]
        return item.tags.get("default") or (next(iter(item.tags.values()), None) if item.tags else None)

    def resolve_tag(self, category_id: str, item_id: str, model_id: str) -> str | None:
        bucket = self._overlay.get(category_id, {})
        if item_id in bucket:
            return self._resolve_tag_from_item(bucket[item_id].item, model_id, category_id, item_id)
        return self._base.resolve_tag(category_id, item_id, model_id)

    def _item_exists(self, category_id: str, item_id: str) -> bool:
        if category_id in self._overlay and item_id in self._overlay[category_id]:
            return True
        cat = self._base.get_category(category_id)
        if cat and any(item.id == item_id for item in cat.items):
            return True
        return False

    def _rename_id(self, category_id: str, item_id: str) -> str:
        if not self._item_exists(category_id, item_id):
            return item_id
        suffix = 2
        while self._item_exists(category_id, f"{item_id}_{suffix}"):
            suffix += 1
        return f"{item_id}_{suffix}"

    def add_item(
        self,
        category_id: str,
        item: TagItem,
        *,
        source: OverlaySource = "import",
        on_conflict: ConflictPolicy = "rename",
        original_phrase: str | None = None,
    ) -> AddItemResult:
        item = copy.deepcopy(item)
        meta = OverlayItemMeta(source=source, original_phrase=original_phrase)
        if item.meta is None:
            item.meta = {}
        item.meta.setdefault("source", source)
        if original_phrase:
            item.meta.setdefault("original_phrase", original_phrase)

        bucket = self._overlay.setdefault(category_id, {})
        action: Literal["added", "skipped", "overwritten", "renamed"] = "added"
        previous_id: str | None = None

        if item.id in bucket:
            if on_conflict == "skip":
                return AddItemResult(item.id, category_id, "skipped", item.id)
            if on_conflict == "overwrite":
                bucket[item.id] = _OverlayEntry(item=item, meta=meta)
                return AddItemResult(item.id, category_id, "overwritten", item.id)
            previous_id = item.id
            item.id = self._rename_id(category_id, item.id)
            action = "renamed"
        elif self._item_exists(category_id, item.id):
            if on_conflict == "skip":
                return AddItemResult(item.id, category_id, "skipped", item.id)
            if on_conflict == "overwrite":
                bucket[item.id] = _OverlayEntry(item=item, meta=meta)
                return AddItemResult(item.id, category_id, "overwritten", item.id)
            previous_id = item.id
            item.id = self._rename_id(category_id, item.id)
            action = "renamed"

        bucket[item.id] = _OverlayEntry(item=item, meta=meta)
        return AddItemResult(item.id, category_id, action, previous_id)

    def update_overlay_item(self, category_id: str, item: TagItem) -> bool:
        bucket = self._overlay.get(category_id)
        if not bucket or item.id not in bucket:
            return False
        existing_meta = bucket[item.id].meta
        cloned = copy.deepcopy(item)
        bucket[item.id] = _OverlayEntry(item=cloned, meta=existing_meta)
        return True

    def move_overlay_item(self, from_category_id: str, to_category_id: str, item_id: str) -> bool:
        from_bucket = self._overlay.get(from_category_id)
        if not from_bucket or item_id not in from_bucket:
            return False
        entry = from_bucket[item_id]
        del from_bucket[item_id]
        if not from_bucket:
            del self._overlay[from_category_id]
        to_bucket = self._overlay.setdefault(to_category_id, {})
        entry.item.id = self._rename_id(to_category_id, entry.item.id)
        to_bucket[entry.item.id] = entry
        return True

    def find_item(self, category_id: str, item_id: str) -> tuple[TagItem | None, bool]:
        bucket = self._overlay.get(category_id, {})
        if item_id in bucket:
            return copy.deepcopy(bucket[item_id].item), True
        category = self._base.get_category(category_id)
        if category is None:
            return None, False
        for item in category.items:
            if item.id == item_id:
                return copy.deepcopy(item), False
        return None, False

    def remove_item(self, category_id: str, item_id: str) -> bool:
        bucket = self._overlay.get(category_id)
        if not bucket or item_id not in bucket:
            return False
        del bucket[item_id]
        if not bucket:
            del self._overlay[category_id]
        return True

    def clear_overlay(self, *, source: OverlaySource | None = None) -> int:
        removed = 0
        if source is None:
            removed = sum(len(bucket) for bucket in self._overlay.values())
            self._overlay.clear()
            return removed
        for category_id in list(self._overlay.keys()):
            bucket = self._overlay[category_id]
            for item_id in list(bucket.keys()):
                if bucket[item_id].meta.source == source:
                    del bucket[item_id]
                    removed += 1
            if not bucket:
                del self._overlay[category_id]
        return removed

    def get_overlay_stats(self) -> dict:
        by_source: dict[str, int] = {"import": 0, "user": 0, "manual": 0}
        by_category: dict[str, int] = {}
        total = 0
        for category_id, bucket in self._overlay.items():
            by_category[category_id] = len(bucket)
            total += len(bucket)
            for entry in bucket.values():
                by_source[entry.meta.source] = by_source.get(entry.meta.source, 0) + 1
        return {"total": total, "by_source": by_source, "by_category": by_category}

    def list_overlay_items(self) -> list[tuple[str, TagItem, OverlayItemMeta]]:
        rows: list[tuple[str, TagItem, OverlayItemMeta]] = []
        for category_id, bucket in sorted(self._overlay.items()):
            for entry in bucket.values():
                rows.append((category_id, entry.item, entry.meta))
        return rows

    def summary(self) -> dict:
        base_summary = self._base.summary()
        overlay_stats = self.get_overlay_stats()
        return {**base_summary, "overlay": overlay_stats}
