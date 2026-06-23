"""Forge / A1111 API integration — send a generated prompt directly to a
locally running Forge (or vanilla A1111) instance via its REST API.

Only the txt2img endpoint is used; no image storage on our side.
The caller receives the raw base64-encoded images from Forge together with
the generation parameters that were actually sent.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Low-level HTTP helper (mirrors the pattern from ollama.py)
# ---------------------------------------------------------------------------


def _request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    timeout: float = 10.0,
) -> dict | None:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Health probe
# ---------------------------------------------------------------------------


def check_forge_health(settings: dict) -> dict:
    """Return a status dict: {ok, reachable, error, sd_model_checkpoint, version}."""
    base_url = settings.get("base_url", "http://127.0.0.1:7860").rstrip("/")
    timeout = float(settings.get("timeout", 10.0))
    try:
        data = _request_json(f"{base_url}/sdapi/v1/options", timeout=timeout) or {}
        return {
            "ok": True,
            "reachable": True,
            "error": None,
            "sd_model_checkpoint": data.get("sd_model_checkpoint", ""),
            "sd_backend": data.get("sd_backend", ""),
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {
            "ok": False,
            "reachable": False,
            "error": str(exc),
            "sd_model_checkpoint": "",
            "sd_backend": "",
        }


def fetch_forge_models(settings: dict) -> list[str]:
    base_url = settings.get("base_url", "http://127.0.0.1:7860").rstrip("/")
    timeout = float(settings.get("catalog_timeout", 30.0))
    try:
        data = _request_json(f"{base_url}/sdapi/v1/sd-models", timeout=timeout) or []
        if not isinstance(data, list):
            logger.warning("fetch_forge_models: unexpected response type %s", type(data))
            return []
        names = sorted(
            {m.get("title") or m.get("model_name") or "" for m in data if m},
            key=str.lower,
        )
        return [n for n in names if n]
    except Exception as exc:
        logger.warning("fetch_forge_models failed: %s", exc)
        return []


def fetch_forge_samplers(settings: dict) -> list[str]:
    base_url = settings.get("base_url", "http://127.0.0.1:7860").rstrip("/")
    timeout = float(settings.get("catalog_timeout", 30.0))
    try:
        data = _request_json(f"{base_url}/sdapi/v1/samplers", timeout=timeout) or []
        if not isinstance(data, list):
            logger.warning("fetch_forge_samplers: unexpected response type %s", type(data))
            return []
        names = sorted(
            {s.get("name") or "" for s in data if s},
            key=str.lower,
        )
        return [n for n in names if n]
    except Exception as exc:
        logger.warning("fetch_forge_samplers failed: %s", exc)
        return []


def fetch_forge_upscalers(settings: dict) -> list[str]:
    base_url = settings.get("base_url", "http://127.0.0.1:7860").rstrip("/")
    timeout = float(settings.get("catalog_timeout", 30.0))
    try:
        data = _request_json(f"{base_url}/sdapi/v1/upscalers", timeout=timeout) or []
        if not isinstance(data, list):
            logger.warning("fetch_forge_upscalers: unexpected response type %s", type(data))
            return []
        names = sorted(
            {u.get("name") or u.get("model_name") or "" for u in data if u},
            key=str.lower,
        )
        result = [n for n in names if n]
        logger.debug("fetch_forge_upscalers: %d items", len(result))
        return result
    except Exception as exc:
        logger.warning("fetch_forge_upscalers failed: %s", exc)
        return []


_SCHEDULER_FALLBACK = [
    "Automatic", "Beta", "DDim", "DDPM", "DPM++ 2M",
    "Euler", "Exponential", "Karras", "LCM", "Linear Quadratic",
    "Polyexponential", "SGM Uniform", "Simple", "Turbo",
]


def fetch_forge_schedulers(settings: dict) -> list[str]:
    base_url = settings.get("base_url", "http://127.0.0.1:7860").rstrip("/")
    timeout = float(settings.get("catalog_timeout", 30.0))
    try:
        data = _request_json(f"{base_url}/sdapi/v1/schedulers", timeout=timeout) or []
        if not isinstance(data, list):
            logger.warning("fetch_forge_schedulers: unexpected response type %s", type(data))
            return _SCHEDULER_FALLBACK
        names = sorted(
            {s.get("label") or s.get("name") or "" for s in data if s},
            key=str.lower,
        )
        result = [n for n in names if n]
        return result if result else _SCHEDULER_FALLBACK
    except Exception as exc:
        logger.warning("fetch_forge_schedulers failed: %s", exc)
        return _SCHEDULER_FALLBACK



def get_forge_progress(settings: dict) -> dict:
    """Poll /sdapi/v1/progress and return a normalised dict.

    Returns:
        progress  float 0–1
        step      int
        steps     int
        phase     "txt2img" | "hires" | "idle"
        eta       float seconds
        image     str | None  base64 preview (may be absent when skip_current_image=True)
    """
    base_url = settings.get("base_url", "http://127.0.0.1:7860").rstrip("/")
    timeout = float(settings.get("timeout", 10.0))
    try:
        data = _request_json(
            f"{base_url}/sdapi/v1/progress?skip_current_image=false",
            timeout=timeout,
        ) or {}
        state = data.get("state") or {}
        progress = float(data.get("progress") or 0.0)
        step = int(state.get("sampling_step") or 0)
        steps = int(state.get("sampling_steps") or 0)
        job_no = int(state.get("job_no") or 0)
        job_count = int(state.get("job_count") or 1)
        # hires fix runs as job_no=1 when job_count=2
        if job_count >= 2 and job_no >= 1:
            phase = "hires"
        elif progress > 0:
            phase = "txt2img"
        else:
            phase = "idle"
        return {
            "ok": True,
            "progress": progress,
            "step": step,
            "steps": steps,
            "phase": phase,
            "eta": float(data.get("eta_relative") or 0.0),
            "image": data.get("current_image"),
            "error": None,
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {
            "ok": False,
            "progress": 0.0,
            "step": 0,
            "steps": 0,
            "phase": "idle",
            "eta": 0.0,
            "image": None,
            "error": str(exc),
        }


def send_to_forge(
    *,
    positive: str,
    negative: str,
    settings: dict,
    override: dict | None = None,
) -> dict[str, Any]:
    """Send a prompt to Forge txt2img and return the response.

    ``override`` can contain any A1111 API parameters that should take
    precedence over the defaults stored in ``settings`` (e.g. steps, cfg,
    width, height, sampler_name, override_settings.sd_model_checkpoint).

    Returns a dict with keys:
        ok          – bool
        images      – list[str]  base64 JPEG strings (empty on failure)
        parameters  – dict       the payload that was actually sent
        info        – dict       the raw ``info`` JSON from Forge (seed, etc.)
        error       – str | None
    """
    base_url = settings.get("base_url", "http://127.0.0.1:7860").rstrip("/")
    # Use a longer timeout for generation (can take 10–120 s depending on
    # hardware/steps) but fall back to 120 s if not configured.
    gen_timeout = float(settings.get("gen_timeout", 120.0))

    payload: dict[str, Any] = {
        "prompt": positive,
        "negative_prompt": negative or "",
        "steps": int(settings.get("default_steps", 20)),
        "cfg_scale": float(settings.get("default_cfg", 7.0)),
        "sampler_name": settings.get("default_sampler", "DPM++ 2M"),
        "scheduler": settings.get("default_scheduler", "Karras"),
        "width": int(settings.get("default_width", 832)),
        "height": int(settings.get("default_height", 1216)),
        "batch_size": max(1, min(4, int(settings.get("batch_size", 1)))),
        "send_images": True,
        "save_images": bool(settings.get("save_images", False)),
    }

    if settings.get("hires_enabled"):
        payload["enable_hr"] = True
        payload["hr_scale"] = float(settings.get("hires_scale", 1.5))
        payload["hr_upscaler"] = settings.get("hires_upscaler", "4x-UltraSharp")
        payload["hr_second_pass_steps"] = int(settings.get("hires_steps", 15))
        payload["denoising_strength"] = float(settings.get("hires_denoising", 0.45))
        resize_x = int(settings.get("hires_resize_x", 0))
        resize_y = int(settings.get("hires_resize_y", 0))
        if resize_x > 0:
            payload["hr_resize_x"] = resize_x
        if resize_y > 0:
            payload["hr_resize_y"] = resize_y
        hires_cfg = float(settings.get("hires_cfg", 0.0))
        if hires_cfg > 0:
            payload["hr_cfg_scale"] = hires_cfg

    checkpoint = settings.get("default_checkpoint", "")
    if checkpoint:
        payload["override_settings"] = {"sd_model_checkpoint": checkpoint}
        payload["override_settings_restore_afterwards"] = True

    # Apply any per-request overrides last so they win over settings defaults.
    if override:
        for k, v in override.items():
            if k == "override_settings" and isinstance(v, dict):
                payload.setdefault("override_settings", {}).update(v)
            else:
                payload[k] = v

    # denoising_strength must be set when enable_hr is True; 0 is valid (no change)
    if payload.get("enable_hr") and "denoising_strength" not in payload:
        payload["denoising_strength"] = 0.45

    try:
        resp = _request_json(
            f"{base_url}/sdapi/v1/txt2img",
            method="POST",
            payload=payload,
            timeout=gen_timeout,
        ) or {}
        images = resp.get("images") or []
        info_raw = resp.get("info") or "{}"
        try:
            info = json.loads(info_raw) if isinstance(info_raw, str) else info_raw
        except json.JSONDecodeError:
            info = {}
        return {
            "ok": True,
            "images": images,
            "parameters": payload,
            "info": info,
            "error": None,
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Forge txt2img request failed: %s", exc)
        return {
            "ok": False,
            "images": [],
            "parameters": payload,
            "info": {},
            "error": str(exc),
        }
