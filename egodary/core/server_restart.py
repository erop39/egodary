"""Reload in-process caches and schedule a uvicorn worker restart."""

from __future__ import annotations

import os
import signal
import threading
import time


def _clear_module_lru_caches(module) -> None:
    for value in vars(module).values():
        if callable(value) and hasattr(value, "cache_clear"):
            value.cache_clear()


def reload_application_caches() -> None:
    from egodary.app import reset_engine_cache
    from egodary.core import conflicts, fetish_skip, rule_matching
    from egodary.core.rules_loader import invalidate_rules_cache

    reset_engine_cache()
    invalidate_rules_cache()
    _clear_module_lru_caches(conflicts)
    _clear_module_lru_caches(rule_matching)
    fetish_skip._SKIP_RULES = None  # noqa: SLF001


def schedule_process_restart(*, delay_seconds: float = 0.4) -> None:
    """Exit the current worker so uvicorn --reload can spawn a fresh process."""

    def _exit_worker() -> None:
        time.sleep(delay_seconds)
        os.kill(os.getpid(), signal.SIGTERM)

    threading.Thread(target=_exit_worker, daemon=True).start()
