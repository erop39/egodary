"""Optional Ollama integration for classify and NSFW refine."""

from __future__ import annotations

import ipaddress
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from egodary.app import get_llm_settings, update_llm_health_cache
from egodary.core.llm_settings import LlmHealthReport, LlmSettings
from egodary.prompting.prompt_analyze.extract_core import CorePrompt
from egodary.prompting.prompt_nsfw_styler.context import NSFW_MUTABLE_SECTIONS, collect_identity_buckets

logger = logging.getLogger(__name__)


def ollama_enabled() -> bool:
    return bool(get_llm_settings().enabled)


def _is_local_host(host: str | None) -> bool:
    if not host:
        return False
    normalized = host.strip("[]").lower()
    if normalized == "localhost":
        return True
    try:
        ip = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_private or ip.is_link_local


def _urlopen(req: urllib.request.Request, *, timeout: float) -> Any:
    host = urllib.parse.urlparse(req.full_url).hostname
    if _is_local_host(host):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        return opener.open(req, timeout=timeout)
    return urllib.request.urlopen(req, timeout=timeout)


def _request_json(url: str, *, method: str = "GET", payload: dict | None = None, timeout: float = 30.0) -> dict | None:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )
    with _urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _parse_json_content(content: str) -> dict:
    text = (content or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            inner = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:]).strip()
            try:
                parsed = json.loads(inner)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _model_matches(selected: str, available: list[str]) -> bool:
    if selected in available:
        return True
    selected_base = selected.split(":", 1)[0]
    return any(name.split(":", 1)[0] == selected_base for name in available)


def _chat(system: str, user: str, *, settings: LlmSettings | None = None) -> str | None:
    settings = settings or get_llm_settings()
    if not settings.enabled:
        return None
    payload = {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": settings.temperature, "top_p": settings.top_p},
        "format": "json",
    }
    url = f"{settings.base_url.rstrip('/')}/api/chat"
    for attempt in range(max(1, int(settings.max_retries) + 1)):
        try:
            body = _request_json(url, method="POST", payload=payload, timeout=settings.timeout)
            message = (body or {}).get("message") or {}
            return message.get("content")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            logger.warning("Ollama request failed (attempt %s): %s", attempt + 1, exc)
    return None


def fetch_ollama_models(settings: LlmSettings | None = None) -> list[str]:
    settings = settings or get_llm_settings()
    try:
        body = _request_json(
            f"{settings.base_url.rstrip('/')}/api/tags",
            timeout=min(settings.timeout, 10.0),
        ) or {}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return []
    models = body.get("models") or []
    out: list[str] = []
    for row in models:
        name = (row or {}).get("name")
        if isinstance(name, str) and name:
            out.append(name)
    return out


def check_ollama_health(settings: LlmSettings | None = None, *, force: bool = False) -> LlmHealthReport:
    settings = settings or get_llm_settings()
    if not settings.enabled:
        report = LlmHealthReport(ok=False, error="LLM is disabled")
        if force:
            update_llm_health_cache(report)
        return report

    if not force and settings.last_health and settings.last_health_at:
        age_seconds = (datetime.now(timezone.utc) - settings.last_health_at).total_seconds()
        if age_seconds <= max(1, settings.health_ttl_seconds):
            return settings.last_health

    started = time.perf_counter()
    models = fetch_ollama_models(settings)
    if not models:
        report = LlmHealthReport(
            ok=False,
            reachable=False,
            error="Ollama is unreachable or returned no models",
            models_available=[],
        )
        update_llm_health_cache(report)
        return report

    model_listed = _model_matches(settings.model, models)
    if not model_listed:
        report = LlmHealthReport(
            ok=False,
            reachable=True,
            model_listed=False,
            error=f"Model '{settings.model}' is not installed",
            models_available=models,
        )
        update_llm_health_cache(report)
        return report

    probe_payload = {
        "model": settings.model,
        "messages": [
            {
                "role": "system",
                "content": 'Reply with JSON only: {"ok": true}',
            }
        ],
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.0, "top_p": 1.0},
    }
    try:
        probe = _request_json(
            f"{settings.base_url.rstrip('/')}/api/chat",
            method="POST",
            payload=probe_payload,
            timeout=settings.timeout,
        ) or {}
        content = ((probe.get("message") or {}).get("content") or "").strip()
        parsed = _parse_json_content(content)
        json_probe_ok = bool(parsed.get("ok") is True)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        json_probe_ok = False

    latency_ms = int((time.perf_counter() - started) * 1000)
    report = LlmHealthReport(
        ok=bool(json_probe_ok),
        reachable=True,
        model_listed=True,
        json_probe_ok=bool(json_probe_ok),
        latency_ms=latency_ms,
        error=None if json_probe_ok else "JSON probe failed",
        models_available=models,
    )
    update_llm_health_cache(report)
    return report


def get_cached_health(settings: LlmSettings | None = None, *, force: bool = False) -> LlmHealthReport:
    return check_ollama_health(settings, force=force)


def classify_phrases_with_ollama(phrases: list[str], core: CorePrompt | None) -> list[dict[str, Any]]:
    settings = get_llm_settings()
    if not settings.enabled:
        return []
    health = get_cached_health(settings)
    if not health.ok:
        return []
    system = (
        "Classify unknown prompt phrases into tag categories. "
        "Do NOT create new tags for phrases that modify locked_buckets. "
        'Return JSON: {"tags": [{"phrase","action","merge_path","category_id","subcategory_id","subgroup","label","variants","conflict_status"}]}'
    )
    user_payload = {
        "unknown_phrases": phrases,
        "locked_buckets": core.locked_buckets() if core else [],
        "locked_paths": sorted(core.locked_paths) if core else [],
        "instruction": "Return only genuinely new concepts.",
    }
    raw = _chat(system, json.dumps(user_payload, ensure_ascii=False), settings=settings)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return list(data.get("tags") or [])


def refine_prompt_with_ollama(
    *,
    before: str,
    intensity: str,
    model_id: str,
    core: CorePrompt | None,
    mutable_fragments: list[str],
    source_prompt: str | None = None,
    assembled_draft: str | None = None,
    unknown_phrases: list[str] | None = None,
    keep_locked: bool = True,
) -> dict[str, Any] | None:
    settings = get_llm_settings()
    if not settings.enabled:
        return None
    health = get_cached_health(settings)
    if not health.ok:
        return None
    prompt_path = Path(__file__).resolve().parents[1] / "prompting" / "prompts" / "nsfw_refine_system.txt"
    system = prompt_path.read_text(encoding="utf-8") if prompt_path.is_file() else ""
    user_payload = {
        "source_prompt": source_prompt or before,
        "assembled_draft": assembled_draft or before,
        "prompt": assembled_draft or before,
        "intensity": intensity,
        "model_id": model_id,
        "keep_identity": keep_locked,
        "identity_buckets": collect_identity_buckets(core) if core and keep_locked else [],
        "mutable_sections": list(NSFW_MUTABLE_SECTIONS),
        "mutable_fragments": mutable_fragments,
        "unknown_phrases": list(unknown_phrases or []),
    }
    raw = _chat(system, json.dumps(user_payload, ensure_ascii=False), settings=settings)
    if not raw:
        return None
    try:
        return _parse_json_content(raw) or json.loads(raw)
    except json.JSONDecodeError:
        return None


def rewrite_prompt_with_ollama(
    *,
    source_prompt: str,
    intensity: str,
    model_id: str,
    core: CorePrompt | None,
    unknown_phrases: list[str] | None = None,
    keep_locked: bool = True,
) -> dict[str, Any] | None:
    settings = get_llm_settings()
    if not settings.enabled:
        return None
    health = get_cached_health(settings)
    if not health.ok:
        return None
    prompt_path = Path(__file__).resolve().parents[1] / "prompting" / "prompts" / "nsfw_rewrite_system.txt"
    system = prompt_path.read_text(encoding="utf-8") if prompt_path.is_file() else ""
    user_payload = {
        "source_prompt": source_prompt,
        "intensity": intensity,
        "model_id": model_id,
        "keep_identity": keep_locked,
        "identity_buckets": collect_identity_buckets(core) if core and keep_locked else [],
        "mutable_sections": list(NSFW_MUTABLE_SECTIONS),
        "unknown_phrases": list(unknown_phrases or []),
    }
    raw = _chat(system, json.dumps(user_payload, ensure_ascii=False), settings=settings)
    if not raw:
        return None
    try:
        parsed = _parse_json_content(raw)
        if parsed:
            return parsed
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def user_rewrite_prompt_with_ollama(
    *,
    source_prompt: str,
    user_instruction: str,
    intensity: str,
    model_id: str,
    unknown_phrases: list[str] | None = None,
) -> dict[str, Any] | None:
    settings = get_llm_settings()
    if not settings.enabled:
        return None
    health = get_cached_health(settings)
    if not health.ok:
        return None
    prompt_path = Path(__file__).resolve().parents[1] / "prompting" / "prompts" / "nsfw_user_rewrite_system.txt"
    system = prompt_path.read_text(encoding="utf-8") if prompt_path.is_file() else ""
    user_payload = {
        "source_prompt": source_prompt,
        "user_instruction": user_instruction.strip(),
        "intensity": intensity,
        "model_id": model_id,
        "unknown_phrases": list(unknown_phrases or []),
    }
    raw = _chat(system, json.dumps(user_payload, ensure_ascii=False), settings=settings)
    if not raw:
        return None
    try:
        parsed = _parse_json_content(raw)
        if parsed:
            return parsed
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def refine_zit_prompt_with_ollama(
    *,
    draft_prompt: str,
    semantics: dict[str, Any],
    paragraph_order: list[str],
) -> dict[str, Any] | None:
    settings = get_llm_settings()
    if not settings.enabled:
        return None
    health = get_cached_health(settings)
    if not health.ok:
        return None
    prompt_path = Path(__file__).resolve().parents[1] / "prompting" / "prompts" / "zit_refine_system.txt"
    system = prompt_path.read_text(encoding="utf-8") if prompt_path.is_file() else ""
    user_payload = {
        "draft_prompt": draft_prompt,
        "semantics": semantics,
        "paragraph_order": paragraph_order,
    }
    raw = _chat(system, json.dumps(user_payload, ensure_ascii=False), settings=settings)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None
