"""Реестр тегов — единая точка, куда контент-пак-плагины складывают свои
категории. Заменяет 244 разрозненные `const`-таблицы оригинала одним
объектом с предсказуемым поведением при конфликтах имён.
"""

from __future__ import annotations

from dataclasses import dataclass

from egodary.core.models import ConflictGroup, TagCategory


class RegistryConflictError(Exception):
    """Дублирующийся id категории или тега внутри категории."""


@dataclass
class _CategoryEntry:
    category: TagCategory
    source_plugin: str


class TagRegistry:
    """Хранит категории тегов и группы конфликтов, наполняется плагинами.

    Дублирующийся id категории или тега внутри категории — это явная ошибка
    загрузки (`RegistryConflictError`), а не молчаливая перезапись: так
    конфликт двух плагинов виден сразу, а не где-то в середине генерации.
    """

    def __init__(self) -> None:
        self._categories: dict[str, _CategoryEntry] = {}
        self._conflicts: list[ConflictGroup] = []

    def register_category(self, category: TagCategory, source_plugin: str) -> None:
        if category.id in self._categories:
            existing = self._categories[category.id]
            raise RegistryConflictError(
                f"Категория '{category.id}' уже зарегистрирована плагином "
                f"'{existing.source_plugin}' (повторная попытка от '{source_plugin}')"
            )
        self._categories[category.id] = _CategoryEntry(category=category, source_plugin=source_plugin)

    def register_conflict_group(self, group: ConflictGroup) -> None:
        self._conflicts.append(group)

    def get_category(self, category_id: str) -> TagCategory | None:
        entry = self._categories.get(category_id)
        return entry.category if entry else None

    def category_ids(self) -> list[str]:
        return sorted(self._categories.keys())

    def all_categories(self) -> list[TagCategory]:
        return [entry.category for entry in self._categories.values()]

    def conflict_groups(self) -> list[ConflictGroup]:
        return list(self._conflicts)

    def source_of(self, category_id: str) -> str | None:
        entry = self._categories.get(category_id)
        return entry.source_plugin if entry else None

    def resolve_tag(self, category_id: str, item_id: str, model_id: str) -> str | None:
        entry = self._categories.get(category_id)
        if not entry:
            return None
        for item in entry.category.items:
            if item.id != item_id:
                continue
            for key in (model_id, "illustrious", "anima", "default"):
                if key in item.tags:
                    return item.tags[key]
                if key == "zimage_turbo" and "zimage" in item.tags:
                    return item.tags["zimage"]
            if "zimage" in item.tags and model_id == "zimage_turbo":
                return item.tags["zimage"]
            return item.tags.get("default") or next(iter(item.tags.values()), None)
        return None

    @property
    def conflicts(self) -> list[ConflictGroup]:
        return self.conflict_groups()

    def summary(self) -> dict:
        """Сводка для debug-снимка: сколько категорий/тегов загружено и откуда."""
        return {
            "category_count": len(self._categories),
            "tag_count": sum(len(e.category.items) for e in self._categories.values()),
            "conflict_group_count": len(self._conflicts),
            "categories": [
                {
                    "id": entry.category.id,
                    "title": entry.category.title,
                    "item_count": len(entry.category.items),
                    "source_plugin": entry.source_plugin,
                }
                for entry in self._categories.values()
            ],
        }
