"""Application bootstrap — load plugins into registry."""

from __future__ import annotations

import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from egodary.bootstrap import build_app
from egodary.core.llm_settings import LlmHealthReport, LlmSettings
from egodary.core.pipeline import PromptEngine
from egodary.core.runtime_registry import RuntimeRegistry
from egodary.logging_setup import setup_logging
from egodary.persistence.db import init_db
from egodary.persistence.schema import load_llm_settings, load_runtime_tag_items_into_registry, save_llm_settings

_CONTENT_DIR = Path(__file__).resolve().parent / "content"
_engine: PromptEngine | None = None
_runtime_registry: RuntimeRegistry | None = None
_engine_content_stamp: float | None = None
_llm_settings: LlmSettings | None = None
_runtime_registry_lock = threading.RLock()
_engine_lock = threading.RLock()
_content_stamp_lock = threading.RLock()
_cached_content_stamp: float | None = None
_cached_content_stamp_checked_at: float = 0.0
_CONTENT_STAMP_TTL_SECONDS = 1.0
_base_registry_lock = threading.RLock()
_base_registry_stamp: float | None = None
_base_registry_cache = None


def content_catalog_stamp() -> float:
    """Latest mtime among built-in content pack files (for cache invalidation)."""
    global _cached_content_stamp, _cached_content_stamp_checked_at
    now = time.perf_counter()
    if _cached_content_stamp is not None and (now - _cached_content_stamp_checked_at) < _CONTENT_STAMP_TTL_SECONDS:
        return _cached_content_stamp

    with _content_stamp_lock:
        now = time.perf_counter()
        if _cached_content_stamp is not None and (now - _cached_content_stamp_checked_at) < _CONTENT_STAMP_TTL_SECONDS:
            return _cached_content_stamp

        latest = 0.0
        if _CONTENT_DIR.is_dir():
            for path in _CONTENT_DIR.rglob("*"):
                if path.is_file():
                    latest = max(latest, path.stat().st_mtime)

        _cached_content_stamp = latest
        _cached_content_stamp_checked_at = time.perf_counter()
        return latest


def _get_base_registry_for_stamp(stamp: float):
    global _base_registry_stamp, _base_registry_cache
    if _base_registry_cache is not None and _base_registry_stamp == stamp:
        return _base_registry_cache

    with _base_registry_lock:
        if _base_registry_cache is not None and _base_registry_stamp == stamp:
            return _base_registry_cache

        base_registry, _ = build_app()
        _base_registry_cache = base_registry
        _base_registry_stamp = stamp
        return _base_registry_cache


def get_runtime_registry(*, force_reload: bool = False) -> RuntimeRegistry:
    """Singleton runtime overlay merged with the latest static registry."""
    global _runtime_registry, _engine_content_stamp
    stamp = content_catalog_stamp()
    needs_rebuild = force_reload or _runtime_registry is None or _engine_content_stamp != stamp
    if needs_rebuild:
        with _runtime_registry_lock:
            if force_reload or _runtime_registry is None or _engine_content_stamp != stamp:
                base_registry = _get_base_registry_for_stamp(stamp)
                if _runtime_registry is None:
                    _runtime_registry = RuntimeRegistry(base_registry)
                else:
                    _runtime_registry.set_base(base_registry)
                load_runtime_tag_items_into_registry(_runtime_registry)
                _engine_content_stamp = stamp
    return _runtime_registry


def create_engine() -> PromptEngine:
    setup_logging("INFO")
    init_db()
    get_llm_settings(force_reload=True)
    registry = get_runtime_registry()
    return PromptEngine(registry)


def get_engine(*, force_reload: bool = False) -> PromptEngine:
    """Return a cached PromptEngine, rebuilding when content catalogs change."""
    global _engine, _engine_content_stamp
    stamp = content_catalog_stamp()
    needs_rebuild = force_reload or _engine is None or _engine_content_stamp != stamp
    if needs_rebuild:
        with _engine_lock:
            if force_reload or _engine is None or _engine_content_stamp != stamp:
                _engine = create_engine()
                _engine_content_stamp = stamp
    return _engine


def reset_engine_cache() -> None:
    global _engine, _runtime_registry, _engine_content_stamp, _llm_settings
    _engine = None
    _runtime_registry = None
    _engine_content_stamp = None
    _llm_settings = None


def get_llm_settings(*, force_reload: bool = False) -> LlmSettings:
    global _llm_settings
    if force_reload or _llm_settings is None:
        _llm_settings = load_llm_settings()
    return _llm_settings


def update_llm_settings(settings: LlmSettings) -> LlmSettings:
    global _llm_settings
    _llm_settings = settings
    save_llm_settings(settings)
    return _llm_settings


def update_llm_health_cache(report: LlmHealthReport | None) -> LlmSettings:
    settings = get_llm_settings()
    settings.last_health = report
    settings.last_health_at = None if report is None else datetime.now(timezone.utc)
    update_llm_settings(settings)
    return settings
