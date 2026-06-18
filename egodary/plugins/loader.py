"""Обнаружение и загрузка плагинов из трёх источников: встроенные паки
(`egodary/content/*`), пользовательские drop-in (`plugins_user/*`) и
установленные через `entry_points` (группа `egodary.plugins`, пока не
используется ни одним реальным пакетом — задел на будущее).
"""

from __future__ import annotations

import importlib.metadata as importlib_metadata
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from egodary._version import APP_VERSION
from egodary.core.models import ConflictGroup, TagCategory, TagItem
from egodary.core.registry import RegistryConflictError, TagRegistry
from egodary.plugins.base import PluginKind
from egodary.plugins.manifest import PluginManifest, parse_manifest

ENTRY_POINT_GROUP = "egodary.plugins"


class PluginLoadError(Exception):
    """Манифест некорректен, версия не подходит или зависимость не найдена."""


@dataclass
class LoadedPlugin:
    manifest: PluginManifest
    source: str  # "builtin" | "dropin" | "installed"
    path: Path | None = None
    category_ids: list[str] = field(default_factory=list)


def _version_satisfies(current: str, requirement: str) -> bool:
    """Минимальная проверка совместимости версий: поддерживает '*' и '>=x.y.z'.

    Сознательно не тянем `packaging` как зависимость на этой фазе — формат
    версий внутри проекта простой (semver-подобный), а более сложные
    спецификаторы (диапазоны, '~=' и т.п.) можно добавить позже, если
    реально понадобятся.
    """
    requirement = requirement.strip()
    if requirement in ("", "*"):
        return True
    if requirement.startswith(">="):
        required = tuple(int(p) for p in requirement[2:].strip().split("."))
        actual = tuple(int(p) for p in current.strip().split("."))
        return actual >= required
    raise PluginLoadError(f"Неподдерживаемый формат requires_core: '{requirement}'")


def _category_from_raw(raw_category: dict) -> TagCategory:
    items = [
        TagItem(
            id=raw["id"],
            label=raw["label"],
            tags=raw.get("tags", {}),
            min_level=raw.get("min_level"),
            meta=raw.get("meta", {}),
        )
        for raw in raw_category.get("items", [])
    ]
    return TagCategory(
        id=raw_category["id"],
        title=raw_category.get("title", raw_category["id"]),
        items=items,
    )


def _load_tag_categories_from_data(data: object) -> list[TagCategory]:
    """Поддерживает оба формата YAML:
    - multi: `categories: [{id, title, items}, ...]`
    - single: `{id, title, items}` на корне файла
    """
    if not isinstance(data, dict):
        return []
    if "categories" in data:
        return [_category_from_raw(raw) for raw in data.get("categories", [])]
    if "id" in data:
        return [_category_from_raw(data)]
    return []


def _load_tag_categories(plugin_dir: Path, tags_file: str) -> list[TagCategory]:
    data = yaml.safe_load((plugin_dir / tags_file).read_text(encoding="utf-8"))
    return _load_tag_categories_from_data(data)


def _load_tag_categories_from_dir(plugin_dir: Path, tags_dir: str) -> list[TagCategory]:
    categories: list[TagCategory] = []
    root = plugin_dir / tags_dir
    for tags_path in sorted(root.glob("*.yaml")):
        data = yaml.safe_load(tags_path.read_text(encoding="utf-8"))
        categories.extend(_load_tag_categories_from_data(data))
    return categories


def _infer_conflict_category_id(ids: list[str]) -> str:
    for entry in ids:
        if ":" in entry:
            return entry.split(":", 1)[0]
    return ""


def _load_conflict_groups(plugin_dir: Path, conflicts_file: str) -> list[ConflictGroup]:
    """`category_id` может быть явным в YAML или выводиться из qualified id
    (`fetish.teasing:dominant` -> `fetish.teasing`).
    """
    data = yaml.safe_load((plugin_dir / conflicts_file).read_text(encoding="utf-8"))
    groups = []
    for group in data.get("groups", []):
        ids = group["ids"]
        category_id = group.get("category_id") or _infer_conflict_category_id(ids)
        groups.append(
            ConflictGroup(
                category_id=category_id,
                ids=ids,
                reason=group.get("reason"),
            )
        )
    return groups


def _discover_manifest_dir(root: Path, source: str) -> list[tuple[PluginManifest, Path, str]]:
    found = []
    if not root.exists():
        return found
    for manifest_path in sorted(root.glob("*/manifest.toml")):
        if manifest_path.parent.name == "rules_pack":
            continue
        manifest = parse_manifest(manifest_path)
        found.append((manifest, manifest_path.parent, source))
    return found


def _discover_installed() -> list[tuple[PluginManifest, Path, str]]:
    found = []
    for ep in importlib_metadata.entry_points(group=ENTRY_POINT_GROUP):
        loader_fn = ep.load()
        manifest, plugin_dir = loader_fn()
        found.append((manifest, plugin_dir, "installed"))
    return found


def _topological_order(
    entries: list[tuple[PluginManifest, Path, str]],
) -> list[tuple[PluginManifest, Path, str]]:
    by_id = {m.plugin.id: (m, p, s) for m, p, s in entries}
    visited: set[str] = set()
    ordered: list[tuple[PluginManifest, Path, str]] = []
    in_progress: set[str] = set()

    def visit(plugin_id: str) -> None:
        if plugin_id in visited:
            return
        if plugin_id in in_progress:
            raise PluginLoadError(f"Циклическая зависимость плагинов на '{plugin_id}'")
        if plugin_id not in by_id:
            raise PluginLoadError(f"Зависимость '{plugin_id}' не найдена среди загружаемых плагинов")
        in_progress.add(plugin_id)
        manifest, _, _ = by_id[plugin_id]
        for dep_id in manifest.plugin.depends_on:
            visit(dep_id)
        in_progress.discard(plugin_id)
        visited.add(plugin_id)
        ordered.append(by_id[plugin_id])

    for plugin_id in by_id:
        visit(plugin_id)
    return ordered


class PluginManager:
    """Оркестрирует обнаружение, проверку совместимости и загрузку плагинов
    в `TagRegistry`. На фазе 1 реально обрабатывает только `kind=content_pack`;
    остальные виды плагинов сохраняются в `loaded` со статусом
    `not_yet_supported`, чтобы команда `egodary plugins list` уже сейчас
    показывала их манифесты, даже до появления нужного исполнителя.
    """

    def __init__(self, builtin_dir: Path, dropin_dir: Path) -> None:
        self.builtin_dir = builtin_dir
        self.dropin_dir = dropin_dir
        self.loaded: list[LoadedPlugin] = []
        self._skipped: list[dict] = []

    def load_all(self, registry: TagRegistry) -> None:
        entries = [
            *_discover_manifest_dir(self.builtin_dir, "builtin"),
            *_discover_manifest_dir(self.dropin_dir, "dropin"),
            *_discover_installed(),
        ]
        ordered = _topological_order(entries)

        for manifest, plugin_dir, source in ordered:
            info = manifest.plugin
            if not _version_satisfies(APP_VERSION, info.requires_core):
                raise PluginLoadError(
                    f"Плагин '{info.id}' требует core {info.requires_core}, текущая версия {APP_VERSION}"
                )

            loaded = LoadedPlugin(manifest=manifest, source=source, path=plugin_dir)

            if info.kind == PluginKind.CONTENT_PACK:
                self._load_content_pack(manifest, plugin_dir, registry, loaded)
            else:
                self._skipped.append({"id": info.id, "kind": info.kind.value, "reason": "пока не реализовано"})

            self.loaded.append(loaded)

    def _load_content_pack(
        self,
        manifest: PluginManifest,
        plugin_dir: Path,
        registry: TagRegistry,
        loaded: LoadedPlugin,
    ) -> None:
        info = manifest.plugin
        content = manifest.content
        if content.tags_file:
            categories = _load_tag_categories(plugin_dir, content.tags_file)
        elif content.tags_dir:
            categories = _load_tag_categories_from_dir(plugin_dir, content.tags_dir)
        else:
            raise PluginLoadError(
                f"content_pack '{info.id}' должен указывать content.tags_file или content.tags_dir"
            )
        if not categories:
            raise PluginLoadError(f"content_pack '{info.id}': файл '{manifest.content.tags_file}' не дал ни одной категории")

        for category in categories:
            try:
                registry.register_category(category, source_plugin=info.id)
            except RegistryConflictError as exc:
                raise PluginLoadError(str(exc)) from exc
            loaded.category_ids.append(category.id)

        if manifest.content.conflicts_file:
            for group in _load_conflict_groups(plugin_dir, manifest.content.conflicts_file):
                registry.register_conflict_group(group)

    def summary(self) -> dict:
        return {
            "loaded_count": len(self.loaded),
            "loaded": [
                {
                    "id": p.manifest.plugin.id,
                    "name": p.manifest.plugin.name,
                    "version": p.manifest.plugin.version,
                    "kind": p.manifest.plugin.kind.value,
                    "source": p.source,
                    "category_ids": p.category_ids,
                }
                for p in self.loaded
            ],
            "skipped_unsupported_kind": self._skipped,
        }
