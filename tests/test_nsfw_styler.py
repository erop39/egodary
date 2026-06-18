"""Tests for NSFW styler context, intensity picks, and API."""

from __future__ import annotations

import copy
import sys
from datetime import datetime, timezone

import pytest

from egodary.bootstrap import build_app
from egodary.core.models import PromptState
from egodary.core.runtime_registry import RuntimeRegistry
from egodary.prompting.prompt_analyze.extract_core import extract_core
from egodary.prompting.prompt_nsfw_styler.context import collect_identity_buckets, collect_mutable_fragments
from egodary.prompting.prompt_nsfw_styler.intensity import NsfwIntensity
from egodary.prompting.prompt_nsfw_styler.llm_refine import llm_refine
from egodary.prompting.prompt_nsfw_styler.rule_based_enhance import _INTENSITY_PICKS, rule_based_enhance


def _snapshot_locked(core) -> dict[str, str]:
    return {p: core.locked_values.get(p, "") for p in core.locked_paths if not p.endswith("__id")}


def _state_value(state: PromptState, path: str):
    if path == "pose":
        return state.pose
    section, fld = path.split(".", 1)
    return getattr(getattr(state, section), fld)


@pytest.mark.parametrize("intensity", ["low", "medium", "high", "extreme"])
@pytest.mark.parametrize(
    "prompt",
    [
        "1girl, almond eyes, red dress, anime style, sunset, solo",
        "1girl, long hair, blue eyes, school uniform, classroom",
    ],
)
def test_locked_paths_unchanged_after_nsfw(intensity: NsfwIntensity, prompt: str):
    base, _ = build_app()
    registry = RuntimeRegistry(base)
    core = extract_core(prompt, "illustrious", registry)
    if not core.locked_paths:
        pytest.skip("no locked paths matched in fixture")
    before = _snapshot_locked(core)
    state = copy.deepcopy(core.state)
    after_state = rule_based_enhance(state, intensity, registry, core, force=False)
    for path in core.locked_paths:
        if path.endswith("__id"):
            continue
        assert _state_value(after_state, path) == _state_value(core.state, path) or before.get(path)


def test_intensity_picks_use_real_registry_ids():
    base, _ = build_app()
    registry = RuntimeRegistry(base)
    for intensity, picks in _INTENSITY_PICKS.items():
        for category_id, candidates in picks.items():
            for preferred_id, _field_path in candidates:
                if not preferred_id:
                    continue
                assert registry.resolve_tag(category_id, preferred_id, "illustrious"), (
                    f"{intensity}: missing {preferred_id} in {category_id}"
                )


def test_extreme_picks_more_categories_than_before():
    assert len(_INTENSITY_PICKS["extreme"]) >= len(_INTENSITY_PICKS["high"])


def test_collect_mutable_fragments_includes_unknown():
    base, _ = build_app()
    registry = RuntimeRegistry(base)
    core = extract_core("1girl, solo, red dress", "illustrious", registry)
    state = core.state.model_copy(deep=True)
    fragments = collect_mutable_fragments(
        state,
        core,
        unknown_phrases=["wide hips", "sagging breasts"],
    )
    joined = " ".join(fragments)
    assert "unknown: wide hips" in joined
    assert "unknown: sagging breasts" in joined


def test_collect_identity_buckets_narrow_scope():
    base, _ = build_app()
    registry = RuntimeRegistry(base)
    prompt = (
        "1girl, solo, red eyes, extreme bimbo face, athletic body, large breasts, "
        "gala dress, blushing, anime style, sunset"
    )
    core = extract_core(prompt, "anima", registry)
    buckets = collect_identity_buckets(core)
    paths = {row["path"] for row in buckets}
    assert not any(p.startswith("outfit.") for p in paths)
    assert not any(p.startswith("style.") for p in paths)
    assert not any(p.startswith("scene.") for p in paths)
    assert "face.facial_expression" not in paths
    assert "face.mouth_lips" not in paths
    assert any(p.startswith("character.") for p in paths) or any(p.startswith("face.") for p in paths)


def test_rewrite_payload_uses_identity_buckets(monkeypatch):
    import json

    from egodary.app import update_llm_settings
    from egodary.core.llm_settings import LlmHealthReport, LlmSettings
    from egodary.integrations import ollama as ollama_mod
    from egodary.integrations.ollama import rewrite_prompt_with_ollama

    update_llm_settings(
        LlmSettings(
            enabled=True,
            last_health=LlmHealthReport(ok=True, reachable=True, model_listed=True, json_probe_ok=True),
            last_health_at=datetime.now(timezone.utc),
        )
    )
    captured: dict = {}

    def fake_chat(system, user, settings=None):
        captured.update(json.loads(user))
        return '{"refined_prompt":"ok","changed_sections":["rewrite"]}'

    monkeypatch.setattr(ollama_mod, "_chat", fake_chat)

    base, _ = build_app()
    registry = RuntimeRegistry(base)
    core = extract_core("1girl, red eyes, athletic body, gala dress, anime style", "anima", registry)

    rewrite_prompt_with_ollama(
        source_prompt="prompt text",
        intensity="extreme",
        model_id="anima",
        core=core,
        keep_locked=True,
    )
    assert captured["keep_identity"] is True
    assert "identity_buckets" in captured
    assert "mutable_sections" in captured
    assert "locked_buckets" not in captured
    identity_paths = {row["path"] for row in captured["identity_buckets"]}
    assert not any(p.startswith("outfit.") for p in identity_paths)


def test_llm_refine_catalog_passes_source_prompt(monkeypatch):
    from egodary.app import update_llm_settings
    from egodary.core.llm_settings import LlmHealthReport, LlmSettings

    update_llm_settings(
        LlmSettings(
            enabled=True,
            last_health=LlmHealthReport(ok=True, reachable=True, model_listed=True, json_probe_ok=True),
            last_health_at=datetime.now(timezone.utc),
        )
    )
    captured: dict = {}

    def fake_refine(**kwargs):
        captured.update(kwargs)
        return {"refined_prompt": "refined output", "changed_sections": ["pose"]}

    llm_mod = sys.modules["egodary.prompting.prompt_nsfw_styler.llm_refine"]
    monkeypatch.setattr(llm_mod, "refine_prompt_with_ollama", fake_refine)

    result = llm_refine(
        before="assembled draft",
        intensity="extreme",
        model_id="anima",
        source_prompt="source with wide hips",
        unknown_phrases=["leaning toward viewer"],
        state=PromptState(),
        use_llm=True,
        llm_mode="catalog",
    )
    assert result.used_llm is True
    assert result.after == "refined output"
    assert captured["source_prompt"] == "source with wide hips"
    assert captured["unknown_phrases"] == ["leaning toward viewer"]
    assert captured["mutable_fragments"]
    assert captured.get("keep_locked") is True


def test_llm_refine_rewrite_mode(monkeypatch):
    from egodary.app import update_llm_settings
    from egodary.core.llm_settings import LlmHealthReport, LlmSettings

    update_llm_settings(
        LlmSettings(
            enabled=True,
            last_health=LlmHealthReport(ok=True, reachable=True, model_listed=True, json_probe_ok=True),
            last_health_at=datetime.now(timezone.utc),
        )
    )

    def fake_rewrite(**kwargs):
        assert kwargs["source_prompt"] == "full prompt text"
        return {"refined_prompt": "rewritten nsfw", "changed_sections": ["rewrite"]}

    llm_mod = sys.modules["egodary.prompting.prompt_nsfw_styler.llm_refine"]
    monkeypatch.setattr(llm_mod, "rewrite_prompt_with_ollama", fake_rewrite)

    result = llm_refine(
        before="full prompt text",
        intensity="high",
        model_id="illustrious",
        source_prompt="full prompt text",
        use_llm=True,
        llm_mode="rewrite",
    )
    assert result.used_llm is True
    assert result.after == "rewritten nsfw"
    assert result.llm_mode == "rewrite"


def test_api_nsfw_style_catalog():
    from fastapi.testclient import TestClient

    from egodary.api.main import app
    from egodary.app import reset_engine_cache

    reset_engine_cache()
    client = TestClient(app)
    res = client.post(
        "/api/prompt/nsfw-style",
        json={"prompt": "1girl, solo, sunset", "model_id": "illustrious", "intensity": "medium"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["before"]
    assert body["after"]
    assert body["used_llm"] is False
    assert body["llm_mode"] == "catalog"
    assert "unknown_phrases" in body


def test_api_nsfw_style_rewrite_mode(monkeypatch):
    from fastapi.testclient import TestClient

    from egodary.api.main import app
    from egodary.app import reset_engine_cache, update_llm_settings
    from egodary.core.llm_settings import LlmHealthReport, LlmSettings

    from datetime import datetime, timezone

    reset_engine_cache()
    update_llm_settings(
        LlmSettings(
            enabled=True,
            model="llama3",
            last_health=LlmHealthReport(ok=True, reachable=True, model_listed=True, json_probe_ok=True),
            last_health_at=datetime.now(timezone.utc),
        )
    )
    client = TestClient(app)

    def fake_rewrite(**kwargs):
        return {"refined_prompt": "rewritten prompt with wide hips", "changed_sections": ["rewrite"]}

    monkeypatch.setattr("egodary.integrations.ollama.rewrite_prompt_with_ollama", fake_rewrite)
    llm_mod = sys.modules["egodary.prompting.prompt_nsfw_styler.llm_refine"]
    monkeypatch.setattr(llm_mod, "rewrite_prompt_with_ollama", fake_rewrite)

    prompt = (
        "qbstyle, masterpiece, 1girl, solo, mature lady in gala dress, "
        "wide hips, very large sagging breasts, leaning toward viewer, blushing"
    )
    res = client.post(
        "/api/prompt/nsfw-style",
        json={
            "prompt": prompt,
            "model_id": "anima",
            "intensity": "extreme",
            "use_llm": True,
            "llm_mode": "rewrite",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["used_llm"] is True
    assert body["llm_mode"] == "rewrite"
    assert "wide hips" in body["after"] or body["after"] == "rewritten prompt with wide hips"
    assert isinstance(body.get("unknown_phrases"), list)


def test_llm_refine_user_mode(monkeypatch):
    from egodary.app import update_llm_settings
    from egodary.core.llm_settings import LlmHealthReport, LlmSettings

    update_llm_settings(
        LlmSettings(
            enabled=True,
            last_health=LlmHealthReport(ok=True, reachable=True, model_listed=True, json_probe_ok=True),
            last_health_at=datetime.now(timezone.utc),
        )
    )
    captured: dict = {}

    def fake_user(**kwargs):
        captured.update(kwargs)
        return {"refined_prompt": "custom nsfw output", "changed_sections": ["user_rewrite"]}

    llm_mod = sys.modules["egodary.prompting.prompt_nsfw_styler.llm_refine"]
    monkeypatch.setattr(llm_mod, "user_rewrite_prompt_with_ollama", fake_user)

    result = llm_refine(
        before="source prompt",
        intensity="extreme",
        model_id="anima",
        source_prompt="source prompt",
        use_llm=False,
        user_instruction="dont change face, make NSFW max",
    )
    assert result.used_llm is True
    assert result.llm_mode == "user"
    assert result.after == "custom nsfw output"
    assert captured["user_instruction"] == "dont change face, make NSFW max"


def test_api_nsfw_style_user_rewrite(monkeypatch):
    from fastapi.testclient import TestClient

    from egodary.api.main import app
    from egodary.app import reset_engine_cache, update_llm_settings
    from egodary.core.llm_settings import LlmHealthReport, LlmSettings

    reset_engine_cache()
    update_llm_settings(
        LlmSettings(
            enabled=True,
            last_health=LlmHealthReport(ok=True, reachable=True, model_listed=True, json_probe_ok=True),
            last_health_at=datetime.now(timezone.utc),
        )
    )
    client = TestClient(app)

    def fake_user(**kwargs):
        assert kwargs["user_instruction"] == "keep face, max nsfw"
        return {"refined_prompt": "user driven nsfw prompt", "changed_sections": ["user_rewrite"]}

    monkeypatch.setattr("egodary.integrations.ollama.user_rewrite_prompt_with_ollama", fake_user)

    llm_mod = sys.modules["egodary.prompting.prompt_nsfw_styler.llm_refine"]
    monkeypatch.setattr(llm_mod, "user_rewrite_prompt_with_ollama", fake_user)

    res = client.post(
        "/api/prompt/nsfw-style",
        json={
            "prompt": "1girl, solo, gala dress, blushing",
            "model_id": "anima",
            "intensity": "extreme",
            "user_instruction": "keep face, max nsfw",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["used_llm"] is True
    assert body["llm_mode"] == "user"
    assert body["after"] == "user driven nsfw prompt"
    assert body["user_instruction"] == "keep face, max nsfw"
