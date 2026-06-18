"""Tests for rules pack loading and user overrides."""

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from egodary.api.main import app
from egodary.core.rules_loader import (
    RULES_SLOT_GENERAL,
    delete_rule_profile,
    get_general_rules,
    get_model_gen_rules,
    invalidate_rules_cache,
    list_rule_profiles,
    load_rules_bundle,
    model_slot,
    reset_user_rules,
    select_rule_profile,
    save_user_rules,
)


@pytest.fixture(autouse=True)
def isolate_rules_user_dir(tmp_path: Path, monkeypatch):
    isolated = tmp_path / "rules_user"
    monkeypatch.setenv("EGODARY_RULES_USER_DIR", str(isolated))
    from egodary.core import rules_loader

    monkeypatch.setattr(rules_loader, "rules_user_dir", lambda: isolated)
    invalidate_rules_cache()
    yield
    invalidate_rules_cache()


def test_general_rules_include_cross_penalties():
    invalidate_rules_cache()
    bundle = get_general_rules()
    assert bundle.penalty_count >= 10
    assert bundle.bonus_count >= 3
    assert bundle.meta.get("id") == "general"
    assert bundle.scoring.get("base_score") == 100


def test_model_gen_rules_loaded():
    invalidate_rules_cache()
    ill = get_model_gen_rules("illustrious")
    anima = get_model_gen_rules("anima")
    zit = get_model_gen_rules("zimage_turbo")
    assert ill.meta.get("prompt_style") == "tags"
    assert anima.format.get("scores_prefix")
    assert zit.meta.get("prompt_style") == "natural_language"


def test_user_rules_override_and_reset():
    invalidate_rules_cache()

    custom = {
        "meta": {"id": "general", "version": "test"},
        "penalties": [
            {
                "id": "test_custom_rule",
                "severity": "soft_warning",
                "emit_warning": True,
                "message": "Custom test rule",
                "when": {"pose_empty": True},
            }
        ],
        "bonuses": [],
    }
    save_user_rules(RULES_SLOT_GENERAL, yaml.dump(custom, allow_unicode=True), name="Custom test")
    bundle = load_rules_bundle(RULES_SLOT_GENERAL)
    assert bundle.source_kind == "user"
    assert any(r.get("id") == "test_custom_rule" for r in bundle.penalties)
    profiles = list_rule_profiles(RULES_SLOT_GENERAL)
    assert len([p for p in profiles["profiles"] if p["kind"] == "user"]) == 1

    reset_user_rules(RULES_SLOT_GENERAL)
    bundle = load_rules_bundle(RULES_SLOT_GENERAL)
    assert bundle.source_kind in {"default", "legacy"}
    assert not any(r.get("id") == "test_custom_rule" for r in bundle.penalties)


def test_user_rules_profiles_select():
    invalidate_rules_cache()
    save_user_rules(
        RULES_SLOT_GENERAL,
        yaml.dump({"meta": {"id": "general"}, "penalties": []}, allow_unicode=True),
        name="Penalties only",
    )
    save_user_rules(
        RULES_SLOT_GENERAL,
        yaml.dump({"meta": {"id": "general"}, "bonuses": []}, allow_unicode=True),
        name="Bonuses only",
    )
    profiles = list_rule_profiles(RULES_SLOT_GENERAL)
    user_profiles = [p for p in profiles["profiles"] if p["kind"] == "user"]
    assert len(user_profiles) >= 2
    second_profile_id = user_profiles[-1]["id"]
    bundle = select_rule_profile(RULES_SLOT_GENERAL, second_profile_id)
    assert bundle.source_profile_id == second_profile_id
    reset_user_rules(RULES_SLOT_GENERAL)
    assert load_rules_bundle(RULES_SLOT_GENERAL).source_profile_id == "default"


def test_user_rules_profile_delete():
    invalidate_rules_cache()
    save_user_rules(
        RULES_SLOT_GENERAL,
        yaml.dump({"meta": {"id": "general"}, "penalties": []}, allow_unicode=True),
        name="To delete",
    )
    profiles = list_rule_profiles(RULES_SLOT_GENERAL)
    user_profiles = [p for p in profiles["profiles"] if p["kind"] == "user"]
    assert user_profiles
    profile_id = user_profiles[-1]["id"]
    bundle = delete_rule_profile(RULES_SLOT_GENERAL, profile_id)
    assert bundle.source_profile_id == "default"
    profiles_after = list_rule_profiles(RULES_SLOT_GENERAL)
    assert not any(p["id"] == profile_id for p in profiles_after["profiles"])


def test_save_user_rules_requires_name_for_new_profile():
    invalidate_rules_cache()
    with pytest.raises(ValueError, match="name"):
        save_user_rules(RULES_SLOT_GENERAL, "meta:\n  id: general\n")


def test_named_profile_labels():
    invalidate_rules_cache()
    save_user_rules(
        RULES_SLOT_GENERAL,
        yaml.dump({"meta": {"id": "general"}, "penalties": []}, allow_unicode=True),
        name="My Custom Rules",
    )
    profiles = list_rule_profiles(RULES_SLOT_GENERAL)
    user_profiles = [p for p in profiles["profiles"] if p["kind"] == "user"]
    assert user_profiles
    assert user_profiles[-1]["label"] == "My Custom Rules"
    assert user_profiles[-1]["id"] == "my_custom_rules"


def test_api_rules_endpoints():
    client = TestClient(app)
    res = client.get("/api/rules")
    assert res.status_code == 200
    slots = {item["slot"] for item in res.json()["slots"]}
    assert RULES_SLOT_GENERAL in slots
    assert model_slot("anima") in slots

    detail = client.get(f"/api/rules/{RULES_SLOT_GENERAL}")
    assert detail.status_code == 200
    assert "yaml" in detail.json()
    assert "profiles" in detail.json()


def test_api_rules_upload_invalid_yaml_returns_400():
    client = TestClient(app)
    res = client.post(
        "/api/rules/upload",
        json={"slot": RULES_SLOT_GENERAL, "profile_id": "default", "yaml": "meta: [invalid"},
    )
    assert res.status_code == 400


def test_api_rules_delete_profile_endpoint():
    client = TestClient(app)
    created = client.post(
        "/api/rules/upload",
        json={
            "slot": RULES_SLOT_GENERAL,
            "profile_id": "default",
            "name": "API test rule",
            "yaml": "meta:\n  id: general\npenalties: []\n",
        },
    )
    assert created.status_code == 200
    profile_id = created.json().get("source_profile_id")
    assert profile_id and profile_id != "default"
    deleted = client.post(
        "/api/rules/delete",
        json={"slot": RULES_SLOT_GENERAL, "profile_id": profile_id},
    )
    assert deleted.status_code == 200
    assert deleted.json().get("source_profile_id") == "default"
