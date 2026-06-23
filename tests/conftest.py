"""Shared pytest fixtures and caches for the test suite."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# PluginManager cache — loading all plugins reads files from disk and takes
# ~1s; share a single loaded instance across the whole session.
# ---------------------------------------------------------------------------

_pm_cache: object | None = None


@pytest.fixture(scope="session")
def loaded_plugin_manager():
    global _pm_cache
    if _pm_cache is None:
        from pathlib import Path
        from egodary.plugins.loader import PluginManager
        from egodary.core.registry import TagRegistry

        root = Path(__file__).resolve().parents[1]
        registry = TagRegistry()
        pm = PluginManager(
            builtin_dir=root / "egodary" / "content",
            dropin_dir=root / "plugins_user",
        )
        pm.load_all(registry)
        _pm_cache = pm
    return _pm_cache
