"""Отладочный снимок состояния приложения.

Прямой аналог вкладки **Debug** из eGen 8.6 (там она показывала bucket-counts,
function guide и т.д.). На этой фазе pipeline ещё нет, поэтому снимок содержит
то, что уже существует: версию, список загруженных плагинов и сводку реестра.
В фазе 3+ сюда добавятся срезы по бакетам промпта (`debug-character`,
`debug-outfit`, ... из оригинала), без изменения публичной функции
`get_debug_snapshot()`.
"""

from __future__ import annotations

from egodary._version import APP_VERSION, BUILD_NUMBER
from egodary.core.registry import TagRegistry
from egodary.plugins.loader import PluginManager


def get_debug_snapshot(registry: TagRegistry, plugin_manager: PluginManager) -> dict:
    """Собрать единый словарь для команды `egodary debug` / debug-API."""
    prefixes: dict[str, int] = {}
    for category_id in registry.category_ids():
        prefix = category_id.split(".", 1)[0]
        prefixes[prefix] = prefixes.get(prefix, 0) + 1

    return {
        "app_version": APP_VERSION,
        "build_number": BUILD_NUMBER,
        "plugins": plugin_manager.summary(),
        "registry": registry.summary(),
        "category_prefixes": prefixes,
    }
