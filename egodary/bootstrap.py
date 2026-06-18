"""Сборка приложения: реестр + менеджер плагинов с уже загруженным контентом.

Используется и CLI, и тестами, и в будущем — Web API (фаза 10), чтобы не
дублировать логику "откуда брать плагины" в нескольких местах.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from egodary.core.registry import TagRegistry
from egodary.plugins.loader import LoadedPlugin, PluginManager

# В editable-установке (`pip install -e .`) структура предсказуема:
# egodary/bootstrap.py -> .parent = пакет egodary/, .parent.parent = корень репозитория.
# Для не-editable инсталляций plugins_user стоит передавать явно через CLI-опцию
# (это ограничение зафиксировано здесь сознательно, а не "забыто").
_PACKAGE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE_DIR.parent
_BUILD_CACHE_LOCK = threading.RLock()
_CACHED_REGISTRY_TEMPLATE: TagRegistry | None = None
_CACHED_PLUGIN_MANAGER_TEMPLATE: PluginManager | None = None
_CACHED_STAMP: float | None = None
_CACHED_DROPIN_DIR: str | None = None
_STAMP_CACHE_LOCK = threading.RLock()
_STAMP_CACHE_KEY: tuple[str, str] | None = None
_STAMP_CACHE_VALUE: float | None = None
_STAMP_CACHE_CHECKED_AT: float = 0.0
_STAMP_CACHE_TTL_SECONDS = 1.0


def _catalog_stamp_for_dirs(builtin_dir: Path, dropin_dir: Path) -> float:
    global _STAMP_CACHE_KEY, _STAMP_CACHE_VALUE, _STAMP_CACHE_CHECKED_AT
    key = (str(builtin_dir.resolve()), str(dropin_dir.resolve()))
    now = time.perf_counter()
    if _STAMP_CACHE_KEY == key and _STAMP_CACHE_VALUE is not None and (now - _STAMP_CACHE_CHECKED_AT) < _STAMP_CACHE_TTL_SECONDS:
        return _STAMP_CACHE_VALUE

    with _STAMP_CACHE_LOCK:
        now = time.perf_counter()
        if _STAMP_CACHE_KEY == key and _STAMP_CACHE_VALUE is not None and (now - _STAMP_CACHE_CHECKED_AT) < _STAMP_CACHE_TTL_SECONDS:
            return _STAMP_CACHE_VALUE

        latest = 0.0
        for root in (builtin_dir, dropin_dir):
            if not root.is_dir():
                continue
            for path in root.rglob("*"):
                if path.is_file():
                    latest = max(latest, path.stat().st_mtime)
        _STAMP_CACHE_KEY = key
        _STAMP_CACHE_VALUE = latest
        _STAMP_CACHE_CHECKED_AT = time.perf_counter()
        return latest


def _clone_registry_template(template: TagRegistry) -> TagRegistry:
    clone = TagRegistry()
    # Fast structural clone: category objects are treated as immutable lookup data.
    clone._categories = dict(template._categories)  # type: ignore[attr-defined]
    clone._conflicts = list(template._conflicts)  # type: ignore[attr-defined]
    return clone


def _clone_plugin_manager_template(
    template: PluginManager,
    *,
    builtin_dir: Path,
    dropin_dir: Path,
) -> PluginManager:
    clone = PluginManager(builtin_dir=builtin_dir, dropin_dir=dropin_dir)
    clone.loaded = [
        LoadedPlugin(
            manifest=loaded.manifest,
            source=loaded.source,
            path=loaded.path,
            category_ids=list(loaded.category_ids),
        )
        for loaded in template.loaded
    ]
    clone._skipped = [dict(item) for item in template._skipped]  # type: ignore[attr-defined]
    return clone


def build_app(plugins_user_dir: Path | None = None) -> tuple[TagRegistry, PluginManager]:
    builtin_dir = _PACKAGE_DIR / "content"
    dropin_dir = plugins_user_dir or (_REPO_ROOT / "plugins_user")
    dropin_dir_str = str(dropin_dir.resolve())
    stamp = _catalog_stamp_for_dirs(builtin_dir, dropin_dir)

    global _CACHED_REGISTRY_TEMPLATE, _CACHED_PLUGIN_MANAGER_TEMPLATE, _CACHED_STAMP, _CACHED_DROPIN_DIR
    if (
        _CACHED_REGISTRY_TEMPLATE is not None
        and _CACHED_PLUGIN_MANAGER_TEMPLATE is not None
        and _CACHED_STAMP == stamp
        and _CACHED_DROPIN_DIR == dropin_dir_str
    ):
        registry = _clone_registry_template(_CACHED_REGISTRY_TEMPLATE)
        plugin_manager = _clone_plugin_manager_template(
            _CACHED_PLUGIN_MANAGER_TEMPLATE,
            builtin_dir=builtin_dir,
            dropin_dir=dropin_dir,
        )
        return registry, plugin_manager

    with _BUILD_CACHE_LOCK:
        if (
            _CACHED_REGISTRY_TEMPLATE is not None
            and _CACHED_PLUGIN_MANAGER_TEMPLATE is not None
            and _CACHED_STAMP == stamp
            and _CACHED_DROPIN_DIR == dropin_dir_str
        ):
            registry = _clone_registry_template(_CACHED_REGISTRY_TEMPLATE)
            plugin_manager = _clone_plugin_manager_template(
                _CACHED_PLUGIN_MANAGER_TEMPLATE,
                builtin_dir=builtin_dir,
                dropin_dir=dropin_dir,
            )
            return registry, plugin_manager

        registry = TagRegistry()
        plugin_manager = PluginManager(builtin_dir=builtin_dir, dropin_dir=dropin_dir)
        plugin_manager.load_all(registry)
        _CACHED_REGISTRY_TEMPLATE = _clone_registry_template(registry)
        _CACHED_PLUGIN_MANAGER_TEMPLATE = _clone_plugin_manager_template(
            plugin_manager,
            builtin_dir=builtin_dir,
            dropin_dir=dropin_dir,
        )
        _CACHED_STAMP = stamp
        _CACHED_DROPIN_DIR = dropin_dir_str
    return registry, plugin_manager
