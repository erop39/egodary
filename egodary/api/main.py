"""FastAPI backend + static web UI."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from egodary.app import (
    get_engine,
    get_llm_settings,
    get_runtime_registry,
    reset_engine_cache,
    update_llm_settings,
)
from egodary.core.llm_settings import LlmHealthReport, LlmSettings
from egodary.core.converter import convert_prompt
from egodary.core.importer import import_prompt_with_report
from egodary.core.models import CharacterLibraryPayload, PromptState, TagItem
from egodary.core.randomizer import apply_god_mode_bundle, smart_randomize
from egodary.core.tag_deduplication import TagDeduplicationService
from egodary.integrations.ollama import check_ollama_health, fetch_ollama_models, get_cached_health
from egodary.persistence.schema import (
    delete_character_preset,
    delete_favorite,
    get_character_preset,
    get_favorite,
    list_character_presets,
    list_favorites,
    migrate_runtime_subgroup_to_subcategory,
    rollback_runtime_subcategory_to_subgroup,
    list_unknown_tags,
    record_unknown_tags,
    save_character_preset,
    save_favorite,
    save_generation_history,
    save_runtime_tag_item,
    set_runtime_tag_item_status,
    update_unknown_tag_by_token,
    update_runtime_tag_item,
    update_favorite,
)

STATIC_DIR = Path(__file__).resolve().parents[1] / "web" / "static"

app = FastAPI(title="eGOdary API", version="0.1.14")


@app.on_event("startup")
def startup_prewarm_engine() -> None:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return
    try:
        get_engine()
    except Exception:
        pass


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/debug")
def debug_snapshot():
    from egodary.bootstrap import build_app
    from egodary.core.debug import get_debug_snapshot

    registry, plugin_manager = build_app()
    return get_debug_snapshot(registry, plugin_manager)


@app.get("/api/changelog")
def changelog():
    path = Path(__file__).resolve().parents[2] / "CHANGELOG.md"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="CHANGELOG.md not found")
    return {"markdown": path.read_text(encoding="utf-8")}


@app.post("/api/conflicts/preview")
def preview_conflicts(state: PromptState):
    from egodary.core.conflicts import preview_state_conflicts

    return {"warnings": preview_state_conflicts(state)}


@app.post("/api/quality/preview")
def preview_quality(state: PromptState):
    from egodary.core.quality_score import compute_quality_score

    return compute_quality_score(state).model_dump()


@app.post("/api/generate")
def generate(state: PromptState):
    from egodary.core.conflicts import preview_state_conflicts
    from egodary.core.quality_score import compute_quality_score

    if state.god_mode_bundle:
        state = apply_god_mode_bundle(state, state.god_mode_bundle)
    warnings = preview_state_conflicts(state)
    quality_score = compute_quality_score(state).model_dump()
    result = get_engine().assemble(state)
    save_generation_history(
        payload={"state": state.model_dump(), "buckets": result.buckets.model_dump()},
        positive=result.positive,
        negative=result.negative,
        model_id=result.model_id,
    )
    return {
        "positive": result.positive,
        "negative": result.negative,
        "model_id": result.model_id,
        "buckets": result.buckets.model_dump(),
        "warnings": warnings,
        "quality_score": quality_score,
    }


@app.post("/api/generate/preview")
def generate_preview(state: PromptState):
    from egodary.core.conflicts import preview_state_conflicts
    from egodary.core.quality_score import compute_quality_score

    if state.god_mode_bundle:
        state = apply_god_mode_bundle(state, state.god_mode_bundle)
    warnings = preview_state_conflicts(state)
    quality_score = compute_quality_score(state).model_dump()
    result = get_engine().assemble(state)
    return {
        "positive": result.positive,
        "negative": result.negative,
        "model_id": result.model_id,
        "buckets": result.buckets.model_dump(),
        "warnings": warnings,
        "quality_score": quality_score,
    }


@app.post("/api/generate/random")
def generate_random(state: PromptState):
    state = smart_randomize(state)
    return generate(state)


class FavoriteRequest(BaseModel):
    name: str
    positive: str
    negative: str | None = None
    model_id: str = "illustrious"
    result_url: str | None = None
    generation_settings: dict | None = None


@app.post("/api/favorites")
def add_favorite(payload: FavoriteRequest):
    try:
        row_id = save_favorite(
            payload.name,
            payload.positive,
            payload.negative,
            payload.model_id,
            result_url=payload.result_url,
            generation_settings=payload.generation_settings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": row_id}


@app.get("/api/favorites")
def get_favorites(limit: int = 50):
    return list_favorites(limit=limit)


@app.get("/api/favorites/{favorite_id}")
def get_favorite_detail(favorite_id: int):
    row = get_favorite(favorite_id)
    if not row:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return row


@app.delete("/api/favorites/{favorite_id}")
def remove_favorite(favorite_id: int):
    if not delete_favorite(favorite_id):
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"ok": True}


@app.put("/api/favorites/{favorite_id}")
def edit_favorite(favorite_id: int, payload: FavoriteRequest):
    try:
        updated = update_favorite(
            favorite_id,
            payload.name,
            payload.positive,
            payload.negative,
            payload.model_id,
            result_url=payload.result_url,
            generation_settings=payload.generation_settings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"ok": True}


@app.get("/api/models/generation-defaults")
def models_generation_defaults():
    from egodary.core.pipeline import ADAPTERS

    out: dict[str, dict] = {}
    for model_id, adapter in ADAPTERS.items():
        defaults = adapter.generation_defaults()
        out[model_id] = {
            "label": adapter.label,
            "supports_negative": adapter.supports_negative,
            "supports_cfg": getattr(adapter, "supports_cfg", True),
            "defaults": {**defaults, "seed": -1},
            "hires": {
                "enabled": False,
                "scale": 2.0,
                "steps": 20,
                "denoising": 0.35,
                "upscaler": "4x-UltraSharp",
            },
        }
    return out


class CharacterLibrarySaveRequest(BaseModel):
    name: str
    payload: CharacterLibraryPayload


@app.post("/api/character-library")
def add_character_preset(body: CharacterLibrarySaveRequest):
    try:
        row_id = save_character_preset(body.name, body.payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": row_id}


@app.get("/api/character-library")
def get_character_library(limit: int = 50):
    return list_character_presets(limit=limit)


@app.get("/api/character-library/{preset_id}")
def get_character_library_item(preset_id: int):
    item = get_character_preset(preset_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Character preset not found")
    return item


@app.delete("/api/character-library/{preset_id}")
def remove_character_preset(preset_id: int):
    if not delete_character_preset(preset_id):
        raise HTTPException(status_code=404, detail="Character preset not found")
    return {"ok": True}


class ConvertRequest(BaseModel):
    prompt: str
    source_model: str
    target_model: str


@app.post("/api/convert")
def convert(payload: ConvertRequest):
    return {"prompt": convert_prompt(payload.prompt, payload.source_model, payload.target_model)}


class ImportRequest(BaseModel):
    prompt: str
    model_id: str = "illustrious"


@app.post("/api/import")
def import_prompt(payload: ImportRequest):
    engine = get_engine()
    result = import_prompt_with_report(payload.prompt, payload.model_id, engine.registry)
    if result.unknown:
        record_unknown_tags(result.unknown, payload.prompt)
    return {
        "state": result.state.model_dump(),
        "report": result.to_report(),
    }


# --- Prompting API ---


class PromptTextRequest(BaseModel):
    prompt: str
    model_id: str = "illustrious"
    source_model: str | None = None
    target_model: str | None = None
    use_llm: bool = False


class PromptImportMergeRequest(BaseModel):
    prompt: str
    model_id: str = "illustrious"
    persist: bool = False
    use_ollama: bool = False
    apply_state: bool = True
    allow_conflicts: bool = False


class PromptImportClassifyRequest(BaseModel):
    prompt: str
    model_id: str = "illustrious"
    use_ollama: bool = False


class PromptNsfwRequest(BaseModel):
    prompt: str | None = None
    state: PromptState | None = None
    model_id: str = "illustrious"
    intensity: str = "medium"
    force: bool = False
    use_llm: bool = False
    llm_mode: str = "catalog"
    keep_locked: bool = True
    user_instruction: str | None = None


class OverlayExportRequest(BaseModel):
    pack_id: str = "imported_pack"


class CreateTagItemRequest(BaseModel):
    label: str
    item_id: str | None = None
    subgroup: str | None = None
    subcategory_id: str | None = None
    persist: bool = True
    source: str = "user"
    tags: dict[str, str] | None = None
    description: str | None = None
    aliases: list[str] | None = None
    default_weight: float = 1.0
    is_active: bool = True
    allow_new_subcategory: bool = False
    dedupe_policy: str = "strict"


class UpdateTagItemRequest(BaseModel):
    label: str | None = None
    tags: dict[str, str] | None = None
    aliases: list[str] | None = None
    description: str | None = None
    subcategory_id: str | None = None
    subgroup: str | None = None
    default_weight: float | None = None
    is_active: bool | None = None
    source: str = "user"
    persist: bool = True
    allow_new_subcategory: bool = False


class MoveTagItemRequest(BaseModel):
    to_category_id: str
    to_subcategory_id: str | None = None
    persist: bool = True
    source: str = "user"


class RuntimeMigrationRequest(BaseModel):
    status: str = "active"


class RuntimeRollbackRequest(BaseModel):
    status: str = "active"


class LlmSettingsRequest(BaseModel):
    enabled: bool = False
    base_url: str = "http://127.0.0.1:11434"
    model: str = "llama3"
    temperature: float = 0.3
    top_p: float = 0.9
    timeout: float = 30.0
    max_retries: int = 1
    health_ttl_seconds: int = 45


def _llm_status() -> dict:
    settings = get_llm_settings()
    health = get_cached_health(settings)
    return {
        "enabled": settings.enabled,
        "healthy": bool(health.ok),
        "model": settings.model,
        "last_error": health.error,
    }


@app.get("/api/llm/settings")
def llm_settings():
    settings = get_llm_settings()
    health = settings.last_health or LlmHealthReport(ok=False, error="Health not checked yet")
    return {
        "settings": settings.to_api_dict(),
        "health": health.model_dump(),
    }


@app.put("/api/llm/settings")
def llm_settings_save(payload: LlmSettingsRequest):
    settings = LlmSettings.model_validate(payload.model_dump())
    update_llm_settings(settings)
    health = check_ollama_health(settings, force=True)
    saved_with_warning = bool(settings.enabled and not health.ok)
    return {
        "settings": get_llm_settings(force_reload=True).to_api_dict(),
        "health": health.model_dump(),
        "saved_with_warning": saved_with_warning,
        "warning": health.error if saved_with_warning else None,
    }


@app.get("/api/llm/models")
def llm_models(base_url: str | None = None):
    settings = get_llm_settings().model_copy(deep=True)
    if base_url:
        settings.base_url = base_url
    models = fetch_ollama_models(settings)
    return {
        "models": models,
        "base_url": settings.base_url,
    }


@app.post("/api/llm/health")
def llm_health(payload: LlmSettingsRequest | None = None):
    settings = get_llm_settings().model_copy(deep=True)
    if payload is not None:
        incoming = payload.model_dump()
        for key, value in incoming.items():
            setattr(settings, key, value)
    health = check_ollama_health(settings, force=True)
    return {
        "health": health.model_dump(),
        "settings": settings.to_api_dict(),
    }


@app.post("/api/prompt/analyze/extract")
def prompt_analyze_extract(payload: PromptTextRequest):
    from egodary.prompting.prompt_analyze.extract_core import extract_core

    registry = get_runtime_registry()
    core = extract_core(payload.prompt, payload.model_id, registry)
    return {
        "core": {
            "locked_paths": sorted(core.locked_paths),
            "locked_values": {k: v for k, v in core.locked_values.items() if not k.endswith("__id")},
            "locked_buckets": core.locked_buckets(),
            "layers": core.layers,
        },
        "state": core.state.model_dump(),
    }


@app.post("/api/prompt/analyze/normalize")
def prompt_analyze_normalize(payload: PromptTextRequest):
    from egodary.prompting.prompt_analyze.normalize_weights import normalize_weights

    result = normalize_weights(payload.prompt)
    return {
        "tokens": [{"text": t.text, "weight": t.weight} for t in result.tokens],
        "clean_prompt": result.clean_prompt,
        "had_weights": result.had_weights,
    }


@app.post("/api/prompt/analyze/convert")
def prompt_analyze_convert(payload: PromptTextRequest):
    from egodary.prompting.prompt_analyze.convert_to_model import convert_analyze

    engine = get_engine()
    registry = get_runtime_registry()
    source = payload.source_model or payload.model_id
    target = payload.target_model or payload.model_id
    result = convert_analyze(
        prompt=payload.prompt,
        source_model=source,
        target_model=target,
        engine=engine,
        registry=registry,
        use_llm=payload.use_llm,
    )
    if result.format == "json":
        return {
            "format": "json",
            "prompt_json": result.prompt_json,
            "model_target": result.model_id,
            "detected_format": result.detected_format,
        }
    response: dict[str, Any] = {
        "format": "text",
        "positive": result.positive,
        "negative": result.negative,
        "model_id": result.model_id,
        "detected_format": result.detected_format,
        "prompt_json": result.prompt_json,
    }
    if result.zit_semantics is not None:
        response["zit_semantics"] = result.zit_semantics
        response["zit_paragraphs"] = result.zit_paragraphs
        response["used_llm"] = result.used_llm
    return response


@app.post("/api/prompt/import/parse")
def prompt_import_parse(payload: PromptTextRequest):
    from egodary.prompting.prompt_import.parse_imported_prompt import parse_imported_prompt

    registry = get_runtime_registry()
    parsed = parse_imported_prompt(payload.prompt, payload.model_id, registry)
    return {
        "state": parsed.state.state.model_dump(),
        "report": parsed.state.to_report(),
        "normalized_clean": parsed.normalized_clean,
        "had_weights": parsed.had_weights,
    }


@app.post("/api/prompt/import/classify")
def prompt_import_classify(payload: PromptImportClassifyRequest):
    from egodary.prompting.prompt_analyze.extract_core import extract_core
    from egodary.prompting.prompt_import.classify_new_tags import classify_new_tags
    from egodary.prompting.prompt_import.parse_imported_prompt import parse_imported_prompt

    registry = get_runtime_registry()
    llm_status = _llm_status()
    if payload.use_ollama and (not llm_status["enabled"] or not llm_status["healthy"]):
        raise HTTPException(status_code=400, detail=llm_status["last_error"] or "LLM is unavailable")
    parsed = parse_imported_prompt(payload.prompt, payload.model_id, registry)
    recorded_unknown_count = record_unknown_tags(parsed.unknown, payload.prompt) if parsed.unknown else 0
    core = extract_core(parsed.normalized_clean, payload.model_id, registry)
    deduped, classified = classify_new_tags(parsed.unknown, core, registry, use_ollama=payload.use_ollama)
    updated_unknown_count = 0
    for entry in classified:
        changed = update_unknown_tag_by_token(
            entry.phrase,
            suggested_category=entry.category_id,
            suggested_subgroup=entry.subgroup,
            suggested_subcategory=entry.subcategory_id,
            resolution_status=entry.conflict_status,
        )
        if changed:
            updated_unknown_count += 1
    for duplicate in deduped:
        changed = update_unknown_tag_by_token(
            duplicate.phrase,
            resolution_status="merge_into_existing" if duplicate.action == "merge_into_existing" else "skipped",
            notes=duplicate.note or None,
        )
        if changed:
            updated_unknown_count += 1
    return {
        "deduped": [d.__dict__ for d in deduped],
        "classified": [
            {
                "phrase": c.phrase,
                "action": c.action,
                "category_id": c.category_id,
                "subgroup": c.subgroup,
                "subcategory_id": c.subcategory_id,
                "label": c.label,
                "conflict_status": c.conflict_status,
                "item_id": c.item.id if c.item else None,
            }
            for c in classified
        ],
        "llm_status": llm_status,
    }


@app.post("/api/prompt/import/merge")
def prompt_import_merge(payload: PromptImportMergeRequest):
    from egodary.prompting.prompt_analyze.extract_core import extract_core
    from egodary.prompting.prompt_import.classify_new_tags import classify_new_tags
    from egodary.prompting.prompt_import.merge_to_registry import merge_to_registry
    from egodary.prompting.prompt_import.parse_imported_prompt import parse_imported_prompt

    registry = get_runtime_registry()
    llm_status = _llm_status()
    if payload.use_ollama and (not llm_status["enabled"] or not llm_status["healthy"]):
        raise HTTPException(status_code=400, detail=llm_status["last_error"] or "LLM is unavailable")
    parsed = parse_imported_prompt(payload.prompt, payload.model_id, registry)
    if parsed.unknown:
        record_unknown_tags(parsed.unknown, payload.prompt)
    core = extract_core(parsed.normalized_clean, payload.model_id, registry)
    deduped, classified = classify_new_tags(parsed.unknown, core, registry, use_ollama=payload.use_ollama)
    merge_report = merge_to_registry(
        classified,
        registry,
        persist=payload.persist,
        reprompt=parsed.normalized_clean,
        model_id=payload.model_id,
        allow_conflicts=payload.allow_conflicts,
    )
    for entry in classified:
        resolution_status = "merged"
        if entry.conflict_status == "hard_conflict" and not payload.allow_conflicts:
            resolution_status = "hard_conflict"
        update_unknown_tag_by_token(
            entry.phrase,
            suggested_category=entry.category_id,
            suggested_subgroup=entry.subgroup,
            suggested_subcategory=entry.subcategory_id,
            resolution_status=resolution_status,
        )
    for duplicate in deduped:
        update_unknown_tag_by_token(
            duplicate.phrase,
            resolution_status="merge_into_existing" if duplicate.action == "merge_into_existing" else "skipped",
            notes=duplicate.note or None,
        )
    state = parsed.state.state
    if payload.apply_state:
        from egodary.core.importer import import_prompt_with_report

        state = import_prompt_with_report(parsed.normalized_clean, payload.model_id, registry).state
    response = {
        "state": state.model_dump(),
        "report": parsed.state.to_report(),
        "deduped": [d.__dict__ for d in deduped],
        "merge_report": {
            "added": [r.__dict__ for r in merge_report.added],
            "skipped": [r.__dict__ for r in merge_report.skipped],
            "reparsed_unknown_count": merge_report.reparsed_unknown_count,
        },
        "overlay": registry.get_overlay_stats(),
        "llm_status": llm_status,
    }
    return response


@app.get("/api/prompt/import/runtime-items")
def prompt_import_runtime_items(limit: int = 200):
    from egodary.persistence.schema import list_runtime_tag_items

    registry = get_runtime_registry()
    return {
        "overlay": registry.get_overlay_stats(),
        "items": list_runtime_tag_items(limit=limit),
        "runtime": [
            {
                "category_id": cid,
                "item": item.model_dump(),
                "source": meta.source,
                "original_phrase": meta.original_phrase,
            }
            for cid, item, meta in registry.list_overlay_items()
        ],
    }


@app.post("/api/prompt/import/export")
def prompt_import_export(payload: OverlayExportRequest):
    from egodary.core.overlay_export import export_overlay_to_plugins_user

    registry = get_runtime_registry()
    paths = export_overlay_to_plugins_user(registry, pack_id=payload.pack_id)
    reset_engine_cache()
    get_engine(force_reload=True)
    return {
        "ok": True,
        "files": [str(p) for p in paths],
        "overlay": get_runtime_registry().get_overlay_stats(),
    }


@app.post("/api/prompt/import/clear-overlay")
def prompt_import_clear_overlay(source: str | None = None):
    registry = get_runtime_registry()
    removed = registry.clear_overlay(source=source)  # type: ignore[arg-type]
    return {"removed": removed, "overlay": registry.get_overlay_stats()}


@app.post("/api/prompt/nsfw-style")
def prompt_nsfw_style(payload: PromptNsfwRequest):
    from egodary.core.importer import import_prompt_with_report
    from egodary.prompting.prompt_analyze.extract_core import extract_core
    from egodary.prompting.prompt_nsfw_styler.intensity import NsfwIntensity
    from egodary.prompting.prompt_nsfw_styler.llm_refine import llm_refine
    from egodary.prompting.prompt_nsfw_styler.rule_based_enhance import rule_based_enhance

    if payload.intensity not in ("low", "medium", "high", "extreme"):
        raise HTTPException(status_code=400, detail="Invalid intensity")
    if payload.llm_mode not in ("catalog", "rewrite", "user"):
        raise HTTPException(status_code=400, detail="Invalid llm_mode")
    intensity: NsfwIntensity = payload.intensity  # type: ignore[assignment]

    user_instruction = (payload.user_instruction or "").strip()
    effective_llm_mode = "user" if user_instruction else payload.llm_mode
    use_llm = payload.use_llm or bool(user_instruction)

    engine = get_engine()
    registry = get_runtime_registry()
    llm_status = _llm_status()
    if use_llm and (not llm_status["enabled"] or not llm_status["healthy"]):
        raise HTTPException(status_code=400, detail=llm_status["last_error"] or "LLM is unavailable")

    unknown_phrases: list[str] = []
    if payload.state is not None:
        state = payload.state.model_copy(deep=True)
        before_asm = engine.assemble(state)
        before = before_asm.positive
        core = extract_core(before, payload.model_id, registry)
        source_prompt = before
    elif payload.prompt:
        import_result = import_prompt_with_report(payload.prompt, payload.model_id, registry)
        unknown_phrases = list(import_result.unknown)
        core = extract_core(payload.prompt, payload.model_id, registry)
        state = core.state.model_copy(deep=True)
        before_asm = engine.assemble(state)
        before = before_asm.positive
        source_prompt = payload.prompt.strip()
    else:
        raise HTTPException(status_code=400, detail="prompt or state required")

    if use_llm and effective_llm_mode in ("rewrite", "user"):
        refine = llm_refine(
            before=source_prompt,
            intensity=intensity,
            model_id=payload.model_id,
            core=core if effective_llm_mode == "rewrite" else None,
            source_prompt=source_prompt,
            unknown_phrases=unknown_phrases,
            use_llm=True,
            llm_mode=effective_llm_mode,  # type: ignore[arg-type]
            keep_locked=payload.keep_locked,
            user_instruction=user_instruction or None,
        )
        return {
            "before": before,
            "after": refine.after,
            "state": state.model_dump(),
            "diff": refine.changed_sections,
            "used_llm": refine.used_llm,
            "llm_mode": refine.llm_mode,
            "intensity": payload.intensity,
            "unknown_phrases": unknown_phrases,
            "user_instruction": user_instruction or None,
            "llm_status": llm_status,
            "llm_error": refine.llm_error,
        }

    enhanced = rule_based_enhance(state, intensity, registry, core, force=payload.force)
    after_asm = engine.assemble(enhanced)
    after = after_asm.positive

    refine = llm_refine(
        before=after,
        intensity=intensity,
        model_id=payload.model_id,
        core=core,
        source_prompt=source_prompt,
        unknown_phrases=unknown_phrases,
        state=enhanced,
        use_llm=use_llm,
        llm_mode="catalog",
        keep_locked=payload.keep_locked,
        user_instruction=user_instruction or None,
    )
    used_llm = refine.used_llm
    if used_llm:
        after = refine.after

    return {
        "before": before,
        "after": after,
        "state": enhanced.model_dump(),
        "diff": refine.changed_sections,
        "used_llm": used_llm,
        "llm_mode": refine.llm_mode,
        "intensity": payload.intensity,
        "unknown_phrases": unknown_phrases,
        "user_instruction": user_instruction or None,
        "llm_status": llm_status,
        "llm_error": refine.llm_error,
    }


@app.get("/api/unknown-tags")
def unknown_tags(status: str = "pending", limit: int = 50):
    return list_unknown_tags(status=status, limit=limit)


@app.get("/api/categories")
def categories():
    engine = get_engine()
    registry = engine.registry
    overlay_stats = registry.get_overlay_stats() if hasattr(registry, "get_overlay_stats") else {}
    return {
        "categories": [
            {"id": cid, "title": registry.get_category(cid).title}
            for cid in registry.category_ids()
            if registry.get_category(cid)
        ],
        "overlay": overlay_stats,
    }


def _slugify_item_id(raw: str) -> str:
    value = raw.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value


def _get_subgroups(items: list[TagItem]) -> set[str]:
    subgroups: set[str] = set()
    for item in items:
        subgroup = (item.meta or {}).get("subgroup")
        if subgroup:
            subgroups.add(str(subgroup))
    return subgroups


def _item_subcategory(item: TagItem) -> str:
    meta = item.meta or {}
    return str(meta.get("subcategory_id") or meta.get("subgroup") or "").strip()


def _get_subcategories(items: list[TagItem]) -> set[str]:
    return {sg for sg in (_item_subcategory(item) for item in items) if sg}


def _normalize_runtime_item_id(payload: CreateTagItemRequest) -> str:
    candidate = payload.item_id or payload.label
    item_id = _slugify_item_id(candidate)
    if not item_id:
        raise HTTPException(status_code=400, detail="item_id is empty after normalization")
    return item_id


def _build_runtime_tags(payload: CreateTagItemRequest) -> dict[str, str]:
    raw_tags = payload.tags or {}
    cleaned_tags = {str(k).strip(): str(v).strip() for k, v in raw_tags.items() if str(v).strip()}
    if not cleaned_tags:
        value = payload.label.strip()
        cleaned_tags = {
            "illustrious": value,
            "anima": value,
            "zimage_turbo": value,
            "default": value,
        }
    else:
        fallback = next(iter(cleaned_tags.values()))
        cleaned_tags.setdefault("default", fallback)
        cleaned_tags.setdefault("illustrious", cleaned_tags["default"])
        cleaned_tags.setdefault("anima", cleaned_tags["default"])
        cleaned_tags.setdefault("zimage_turbo", cleaned_tags["default"])
    return cleaned_tags


def _normalize_aliases(values: list[str] | None) -> list[str]:
    aliases = []
    for value in values or []:
        cleaned = str(value).strip()
        if cleaned and cleaned not in aliases:
            aliases.append(cleaned)
    return aliases


def _build_runtime_meta(
    *,
    label: str,
    subcategory_id: str,
    source: str,
    description: str | None,
    aliases: list[str] | None,
    default_weight: float,
    is_active: bool = True,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "subcategory_id": subcategory_id,
        "subgroup": subcategory_id,
        "normalized_name": label.strip().lower(),
        "aliases": _normalize_aliases(aliases),
        "default_weight": float(default_weight),
        "is_active": bool(is_active),
        "source": source,
    }
    if description and description.strip():
        meta["description"] = description.strip()
    return meta


@app.get("/api/categories/{category_id}")
def category_detail(category_id: str):
    engine = get_engine()
    category = engine.registry.get_category(category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    overlay_ids: set[str] = set()
    registry = engine.registry
    if hasattr(registry, "list_overlay_items"):
        overlay_ids = {item.id for cid, item, _ in registry.list_overlay_items() if cid == category_id}
    items_payload = [
        {
            **item.model_dump(),
            "overlay": item.id in overlay_ids,
        }
        for item in category.items
    ]
    subcategories = sorted(_get_subcategories(category.items))
    response = {
        "id": category.id,
        "title": category.title,
        "subcategories": subcategories,
        "items": items_payload,
    }
    return response


@app.post("/api/categories/{category_id}/items")
def category_add_item(category_id: str, payload: CreateTagItemRequest):
    registry = get_runtime_registry()
    category = registry.get_category(category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    label = payload.label.strip()
    if not label:
        raise HTTPException(status_code=400, detail="label is required")

    allowed_subcategories = _get_subcategories(category.items)
    subcategory_id = (payload.subcategory_id or payload.subgroup or "").strip()
    if allowed_subcategories and subcategory_id not in allowed_subcategories and not payload.allow_new_subcategory:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid subcategory '{subcategory_id}'. "
                f"Allowed: {', '.join(sorted(allowed_subcategories))}. "
                "Use allow_new_subcategory=true to create a new one."
            ),
        )

    dedupe_service = TagDeduplicationService()
    dedupe_matches = dedupe_service.find_matches(phrase=label, category_id=category_id, items=category.items)
    hard_conflicts = [m for m in dedupe_matches if m.match_type in {"exact_name", "alias_collision"}]
    if hard_conflicts and payload.dedupe_policy != "allow":
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Tag duplicates existing item in category",
                "matches": [m.__dict__ for m in hard_conflicts],
            },
        )

    source = payload.source if payload.source in {"import", "user", "manual"} else "user"
    item = TagItem(
        id=_normalize_runtime_item_id(payload),
        label=label,
        tags=_build_runtime_tags(payload),
        meta=_build_runtime_meta(
            label=label,
            subcategory_id=subcategory_id,
            source=source,
            description=payload.description,
            aliases=payload.aliases,
            default_weight=payload.default_weight,
            is_active=payload.is_active,
        ),
    )
    add_result = registry.add_item(
        category_id,
        item,
        source=source,
        on_conflict="rename",
    )
    added_item = registry.get_category(category_id)
    created = next((i for i in (added_item.items if added_item else []) if i.id == add_result.item_id), None)
    if created is None:
        raise HTTPException(status_code=500, detail="Unable to resolve created item")
    if payload.persist:
        save_runtime_tag_item(
            category_id,
            created,
            source=source,
        )
    return {
        "category_id": category_id,
        "item": {**created.model_dump(), "overlay": True},
        "persisted": bool(payload.persist),
        "action": add_result.action,
        "previous_id": add_result.previous_id,
        "dedupe_matches": [m.__dict__ for m in dedupe_matches],
        "overlay": registry.get_overlay_stats(),
    }


@app.get("/api/tag-studio/items")
def tag_studio_items(
    q: str | None = None,
    category_id: str | None = None,
    subcategory_id: str | None = None,
    active_only: bool = True,
    limit: int = 500,
):
    registry = get_runtime_registry()
    rows: list[dict[str, Any]] = []
    q_norm = (q or "").strip().lower()
    for cid in registry.category_ids():
        if category_id and cid != category_id:
            continue
        category = registry.get_category(cid)
        if category is None:
            continue
        for item in category.items:
            meta = item.meta or {}
            item_subcategory = _item_subcategory(item)
            if subcategory_id and item_subcategory != subcategory_id:
                continue
            if active_only and meta.get("is_active") is False:
                continue
            if q_norm:
                haystack = " ".join(
                    [
                        item.label.lower(),
                        str(meta.get("description") or "").lower(),
                        " ".join(str(alias).lower() for alias in (meta.get("aliases") or [])),
                    ]
                )
                if q_norm not in haystack:
                    continue
            rows.append(
                {
                    "category_id": cid,
                    "subcategory_id": item_subcategory,
                    "item": item.model_dump(),
                    "overlay": False,
                }
            )
            if len(rows) >= limit:
                return {"items": rows, "count": len(rows)}
    return {"items": rows, "count": len(rows)}


@app.put("/api/categories/{category_id}/items/{item_id}")
def category_update_item(category_id: str, item_id: str, payload: UpdateTagItemRequest):
    registry = get_runtime_registry()
    item, is_overlay = registry.find_item(category_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    if not is_overlay:
        raise HTTPException(status_code=400, detail="Only runtime overlay items are editable")

    if payload.label is not None:
        label = payload.label.strip()
        if not label:
            raise HTTPException(status_code=400, detail="label must not be empty")
        item.label = label
        item.meta["normalized_name"] = label.lower()
    if payload.tags is not None:
        item.tags = _build_runtime_tags(
            CreateTagItemRequest(
                label=item.label,
                tags=payload.tags,
                subgroup=_item_subcategory(item),
            )
        )
    if payload.aliases is not None:
        item.meta["aliases"] = _normalize_aliases(payload.aliases)
    if payload.description is not None:
        item.meta["description"] = payload.description.strip()
    if payload.default_weight is not None:
        item.meta["default_weight"] = float(payload.default_weight)
    if payload.is_active is not None:
        item.meta["is_active"] = bool(payload.is_active)

    new_subcategory = (payload.subcategory_id or payload.subgroup or "").strip()
    if new_subcategory:
        allowed_subcategories = _get_subcategories(registry.get_category(category_id).items)
        if allowed_subcategories and new_subcategory not in allowed_subcategories and not payload.allow_new_subcategory:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid subcategory '{new_subcategory}'. "
                    "Use allow_new_subcategory=true to create a new one."
                ),
            )
        item.meta["subcategory_id"] = new_subcategory
        item.meta["subgroup"] = new_subcategory

    if not registry.update_overlay_item(category_id, item):
        raise HTTPException(status_code=500, detail="Unable to update overlay item")

    source = payload.source if payload.source in {"import", "user", "manual"} else "user"
    if payload.persist:
        updated = update_runtime_tag_item(category_id, item.id, item, source=source)
        if not updated:
            save_runtime_tag_item(category_id, item, source=source)
    return {"category_id": category_id, "item": item.model_dump(), "overlay": registry.get_overlay_stats()}


@app.post("/api/categories/{category_id}/items/{item_id}/move")
def category_move_item(category_id: str, item_id: str, payload: MoveTagItemRequest):
    registry = get_runtime_registry()
    item, is_overlay = registry.find_item(category_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    if not is_overlay:
        raise HTTPException(status_code=400, detail="Only runtime overlay items are movable")
    target_category = registry.get_category(payload.to_category_id)
    if target_category is None:
        raise HTTPException(status_code=404, detail="Target category not found")

    target_subcategory = (payload.to_subcategory_id or _item_subcategory(item) or "").strip()
    if target_subcategory:
        item.meta["subcategory_id"] = target_subcategory
        item.meta["subgroup"] = target_subcategory
        registry.update_overlay_item(category_id, item)

    moved = registry.move_overlay_item(category_id, payload.to_category_id, item_id)
    if not moved:
        raise HTTPException(status_code=500, detail="Unable to move overlay item")

    source = payload.source if payload.source in {"import", "user", "manual"} else "user"
    if payload.persist:
        set_runtime_tag_item_status(category_id, item_id, "moved")
        save_runtime_tag_item(payload.to_category_id, item, source=source)
    return {"ok": True, "overlay": registry.get_overlay_stats()}


@app.post("/api/categories/{category_id}/items/{item_id}/deactivate")
def category_deactivate_item(category_id: str, item_id: str, persist: bool = True):
    registry = get_runtime_registry()
    item, is_overlay = registry.find_item(category_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    if not is_overlay:
        raise HTTPException(status_code=400, detail="Only runtime overlay items can be deactivated")

    item.meta["is_active"] = False
    if not registry.update_overlay_item(category_id, item):
        raise HTTPException(status_code=500, detail="Unable to deactivate item")
    if persist:
        set_runtime_tag_item_status(category_id, item_id, "inactive")
        update_runtime_tag_item(category_id, item_id, item, source="user")
    return {"ok": True, "item": item.model_dump(), "overlay": registry.get_overlay_stats()}


@app.get("/api/tag-studio/deduplicate")
def tag_studio_deduplicate(category_id: str | None = None, fuzzy_threshold: float = 0.9):
    registry = get_runtime_registry()
    service = TagDeduplicationService(fuzzy_threshold=fuzzy_threshold)
    findings: list[dict[str, Any]] = []
    for cid in registry.category_ids():
        if category_id and cid != category_id:
            continue
        category = registry.get_category(cid)
        if category is None:
            continue
        for item in category.items:
            matches = service.find_matches(phrase=item.label, category_id=cid, items=category.items)
            for match in matches:
                if match.item_id == item.id:
                    continue
                findings.append(
                    {
                        "category_id": cid,
                        "source_item_id": item.id,
                        "source_label": item.label,
                        "match": match.__dict__,
                    }
                )
    return {"findings": findings, "count": len(findings)}


@app.post("/api/tag-studio/migrate/runtime-subcategory")
def tag_studio_migrate_runtime_subcategory(payload: RuntimeMigrationRequest):
    result = migrate_runtime_subgroup_to_subcategory(status=payload.status)
    return {"ok": True, **result}


@app.post("/api/tag-studio/rollback/runtime-subcategory")
def tag_studio_rollback_runtime_subcategory(payload: RuntimeRollbackRequest):
    result = rollback_runtime_subcategory_to_subgroup(status=payload.status)
    return {"ok": True, **result}


class RulesUploadRequest(BaseModel):
    slot: str
    yaml: str
    profile_id: str = "default"
    name: str | None = None


class RulesSlotRequest(BaseModel):
    slot: str


class RulesSelectRequest(BaseModel):
    slot: str
    profile_id: str


class RulesDeleteRequest(BaseModel):
    slot: str
    profile_id: str


@app.get("/api/rules")
def rules_list():
    from egodary.core.rules_loader import list_rules_slots

    return {"slots": list_rules_slots()}


@app.get("/api/rules/{slot:path}")
def rules_detail(slot: str):
    from egodary.core.rules_loader import (
        list_rule_profiles,
        load_rules_bundle,
        read_rules_text,
    )

    try:
        bundle = load_rules_bundle(slot)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        **bundle.summary(),
        "yaml": read_rules_text(slot),
        **list_rule_profiles(slot),
    }


@app.post("/api/rules/upload")
def rules_upload(payload: RulesUploadRequest):
    from egodary.core.rules_loader import save_user_rules

    try:
        bundle = save_user_rules(payload.slot, payload.yaml, payload.profile_id, payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return bundle.summary()


@app.post("/api/rules/reset")
def rules_reset(payload: RulesSlotRequest):
    from egodary.core.rules_loader import reset_user_rules

    try:
        bundle = reset_user_rules(payload.slot)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return bundle.summary()


@app.post("/api/rules/select")
def rules_select(payload: RulesSelectRequest):
    from egodary.core.rules_loader import select_rule_profile

    try:
        bundle = select_rule_profile(payload.slot, payload.profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return bundle.summary()


@app.post("/api/rules/delete")
def rules_delete(payload: RulesDeleteRequest):
    from egodary.core.rules_loader import delete_rule_profile

    try:
        bundle = delete_rule_profile(payload.slot, payload.profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return bundle.summary()


@app.post("/api/server/restart")
def server_restart():
    from egodary.core.server_restart import reload_application_caches, schedule_process_restart

    reload_application_caches()
    schedule_process_restart()
    return {
        "ok": True,
        "message": "Server is restarting. Reload the page if it does not recover automatically.",
    }


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(STATIC_DIR / "img" / "favicon.png", media_type="image/png")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
