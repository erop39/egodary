"""Load and resolve general compatibility + per-model generation rule packs.

Resolution order (per slot):
  1. User override in ``rules_user/`` (if present)
  2. Built-in pack in ``content/rules_pack/``
  3. Legacy fallback for general rules: ``content/cross_rules.yaml``

User can upload YAML via API; ``POST /api/rules/reset`` removes the override.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_PROFILE_META_FILE = "profiles_meta.yaml"
_RESERVED_PROFILE_IDS = frozenset({"default", "profiles_meta"})

RULES_SLOT_GENERAL = "general"
RULES_SLOT_MODEL_PREFIX = "model:"

MODEL_RULE_IDS = ("illustrious", "anima", "zimage_turbo")

_PACKAGE_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_CONTENT_DIR = _PACKAGE_DIR / "content"
_DEFAULT_RULES_PACK = _DEFAULT_CONTENT_DIR / "rules_pack"
_DEFAULT_RULES_USER = _PACKAGE_DIR.parent / "rules_user"


@dataclass
class RulesBundle:
    """Resolved rule document for one slot (general or model-specific)."""

    slot: str
    meta: dict[str, Any] = field(default_factory=dict)
    penalties: list[dict[str, Any]] = field(default_factory=list)
    bonuses: list[dict[str, Any]] = field(default_factory=list)
    scoring: dict[str, Any] = field(default_factory=dict)
    policies: list[dict[str, Any]] = field(default_factory=list)
    format: dict[str, Any] = field(default_factory=dict)
    generation_defaults: dict[str, Any] = field(default_factory=dict)
    negative: dict[str, Any] = field(default_factory=dict)
    source_path: str = ""
    source_kind: str = "default"  # default | user | legacy
    source_profile_id: str = "default"

    @property
    def penalty_count(self) -> int:
        return len(self.penalties)

    @property
    def bonus_count(self) -> int:
        return len(self.bonuses)

    def summary(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "meta": self.meta,
            "source_path": self.source_path,
            "source_kind": self.source_kind,
            "source_profile_id": self.source_profile_id,
            "penalty_count": len(self.penalties),
            "bonus_count": len(self.bonuses),
            "has_format": bool(self.format),
            "has_scoring": bool(self.scoring),
            "profile_name": self.meta.get("profile_name"),
        }


def rules_user_dir() -> Path:
    try:
        from egodary.config import get_settings

        return get_settings().rules_user_dir
    except Exception:
        return _PACKAGE_DIR.parent / "rules_user"


def rules_pack_dir() -> Path:
    try:
        from egodary.config import get_settings

        return get_settings().content_dir / "rules_pack"
    except Exception:
        return _DEFAULT_RULES_PACK


def model_slot(model_id: str) -> str:
    return f"{RULES_SLOT_MODEL_PREFIX}{model_id}"


def parse_slot(slot: str) -> tuple[str, str | None]:
    if slot == RULES_SLOT_GENERAL:
        return "general", None
    if slot.startswith(RULES_SLOT_MODEL_PREFIX):
        return "model", slot[len(RULES_SLOT_MODEL_PREFIX) :]
    raise ValueError(f"Unknown rules slot: {slot}")


def _slot_path(kind: str, model_id: str | None, *, user: bool) -> Path:
    root = rules_user_dir() if user else rules_pack_dir()
    if kind == "general":
        return root / "general.yaml"
    assert model_id
    return root / "models" / f"{model_id}.yaml"


def _slot_slug(slot: str) -> str:
    return slot.replace(":", "__")


def _profiles_dir(slot: str) -> Path:
    return rules_user_dir() / "profiles" / _slot_slug(slot)


def _active_profiles_path() -> Path:
    return rules_user_dir() / "active_profiles.yaml"


def _load_active_profiles() -> dict[str, str]:
    path = _active_profiles_path()
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if k and v}


def _save_active_profiles(mapping: dict[str, str]) -> None:
    path = _active_profiles_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(mapping, allow_unicode=True, sort_keys=True), encoding="utf-8")


def _profile_meta_path(slot: str) -> Path:
    return _profiles_dir(slot) / _PROFILE_META_FILE


def _load_profile_meta(slot: str) -> dict[str, dict[str, Any]]:
    path = _profile_meta_path(slot)
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    return {str(k): dict(v) for k, v in data.items() if isinstance(v, dict)}


def _save_profile_meta(slot: str, meta: dict[str, dict[str, Any]]) -> None:
    path = _profile_meta_path(slot)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(meta, allow_unicode=True, sort_keys=True), encoding="utf-8")


def _set_profile_meta(slot: str, profile_id: str, patch: dict[str, Any]) -> None:
    meta = _load_profile_meta(slot)
    entry = dict(meta.get(profile_id) or {})
    entry.update(patch)
    meta[profile_id] = entry
    _save_profile_meta(slot, meta)


def _remove_profile_meta(slot: str, profile_id: str) -> None:
    meta = _load_profile_meta(slot)
    if profile_id in meta:
        meta.pop(profile_id, None)
        _save_profile_meta(slot, meta)


def _slugify_profile_name(name: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", name.strip().lower(), flags=re.UNICODE)
    slug = re.sub(r"[\s-]+", "_", slug).strip("_")
    return slug or "rule"


def _list_profile_ids(slot: str) -> set[str]:
    profile_dir = _profiles_dir(slot)
    if not profile_dir.is_dir():
        return set()
    return {
        path.stem
        for path in profile_dir.glob("*.yaml")
        if path.name != _PROFILE_META_FILE and path.stem not in _RESERVED_PROFILE_IDS
    }


def _unique_profile_id(slot: str, base_slug: str) -> str:
    existing = _list_profile_ids(slot)
    if base_slug not in existing:
        return base_slug
    index = 2
    while f"{base_slug}_{index}" in existing:
        index += 1
    return f"{base_slug}_{index}"


def _profile_label(slot: str, profile_id: str) -> str:
    entry = _load_profile_meta(slot).get(profile_id) or {}
    name = entry.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    if profile_id.startswith("user_rule_"):
        suffix = profile_id.removeprefix("user_rule_")
        if suffix.isdigit():
            return f"User rule {suffix}"
    return profile_id.replace("_", " ")


def _profile_path(slot: str, profile_id: str) -> Path:
    return _profiles_dir(slot) / f"{profile_id}.yaml"


def _deep_merge_dict(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in overlay.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge_dict(out[key], value)
        else:
            out[key] = value
    return out


def _merge_rule_lists(existing: list[dict], incoming: list[dict]) -> list[dict]:
    seen: set[str] = set()
    merged: list[dict] = []
    for item in existing + incoming:
        rule_id = item.get("id")
        if rule_id:
            if rule_id in seen:
                continue
            seen.add(rule_id)
        merged.append(item)
    return merged


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _resolve_includes(data: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    includes = data.pop("includes", None) or []
    if not includes:
        return data

    merged: dict[str, Any] = {
        "penalties": [],
        "bonuses": [],
        "scoring": {},
        "policies": [],
        "format": {},
        "generation_defaults": {},
        "negative": {},
        "meta": {},
    }
    for entry in includes:
        include_path = (base_dir / str(entry)).resolve()
        included = _load_yaml(include_path)
        included = _resolve_includes(included, include_path.parent)
        merged["penalties"] = _merge_rule_lists(merged["penalties"], included.get("penalties") or [])
        merged["bonuses"] = _merge_rule_lists(merged["bonuses"], included.get("bonuses") or [])
        merged["policies"] = _merge_rule_lists(merged["policies"], included.get("policies") or [])
        merged["scoring"] = _deep_merge_dict(merged["scoring"], included.get("scoring") or {})
        merged["format"] = _deep_merge_dict(merged["format"], included.get("format") or {})
        merged["generation_defaults"] = _deep_merge_dict(
            merged["generation_defaults"], included.get("generation_defaults") or {}
        )
        merged["negative"] = _deep_merge_dict(merged["negative"], included.get("negative") or {})
        merged["meta"] = _deep_merge_dict(merged["meta"], included.get("meta") or {})

    merged["penalties"] = _merge_rule_lists(merged["penalties"], data.get("penalties") or [])
    merged["bonuses"] = _merge_rule_lists(merged["bonuses"], data.get("bonuses") or [])
    merged["policies"] = _merge_rule_lists(merged["policies"], data.get("policies") or [])
    merged["scoring"] = _deep_merge_dict(merged["scoring"], data.get("scoring") or {})
    merged["format"] = _deep_merge_dict(merged["format"], data.get("format") or {})
    merged["generation_defaults"] = _deep_merge_dict(
        merged["generation_defaults"], data.get("generation_defaults") or {}
    )
    merged["negative"] = _deep_merge_dict(merged["negative"], data.get("negative") or {})
    merged["meta"] = _deep_merge_dict(merged["meta"], data.get("meta") or {})
    return merged


def _bundle_from_raw(slot: str, raw: dict[str, Any], path: Path, source_kind: str) -> RulesBundle:
    resolved = _resolve_includes(dict(raw), path.parent)
    fmt = dict(resolved.get("format") or {})
    generation_defaults = dict(resolved.get("generation_defaults") or {})
    nested_gen = fmt.pop("generation_defaults", None)
    if isinstance(nested_gen, dict):
        generation_defaults = _deep_merge_dict(generation_defaults, nested_gen)
    profile_id = "default" if source_kind != "user" else path.stem
    meta = dict(resolved.get("meta") or {})
    if source_kind == "user":
        meta["profile_name"] = _profile_label(slot, profile_id)
    return RulesBundle(
        slot=slot,
        meta=meta,
        penalties=list(resolved.get("penalties") or []),
        bonuses=list(resolved.get("bonuses") or []),
        scoring=dict(resolved.get("scoring") or {}),
        policies=list(resolved.get("policies") or []),
        format=fmt,
        generation_defaults=generation_defaults,
        negative=dict(resolved.get("negative") or {}),
        source_path=str(path),
        source_kind=source_kind,
        source_profile_id=profile_id,
    )


def _load_slot(slot: str) -> RulesBundle:
    kind, model_id = parse_slot(slot)
    active_profiles = _load_active_profiles()
    active_profile_id = active_profiles.get(slot, "default")
    if active_profile_id != "default":
        active_path = _profile_path(slot, active_profile_id)
        if active_path.is_file():
            return _bundle_from_raw(slot, _load_yaml(active_path), active_path, "user")

    # Backward compatibility with legacy single override files.
    user_path = _slot_path(kind, model_id, user=True)
    if user_path.is_file():
        return _bundle_from_raw(slot, _load_yaml(user_path), user_path, "user")

    default_path = _slot_path(kind, model_id, user=False)
    if default_path.is_file():
        return _bundle_from_raw(slot, _load_yaml(default_path), default_path, "default")

    if kind == "general":
        legacy = _DEFAULT_CONTENT_DIR / "cross_rules.yaml"
        if legacy.is_file():
            bundle = _bundle_from_raw(slot, _load_yaml(legacy), legacy, "legacy")
            bundle.meta.setdefault("id", "general")
            bundle.meta.setdefault("title", "General compatibility rules")
            return bundle

    return RulesBundle(slot=slot, meta={"id": slot}, source_path="", source_kind="default")


def invalidate_rules_cache() -> None:
    load_rules_bundle.cache_clear()
    get_general_rules.cache_clear()
    get_model_gen_rules.cache_clear()
    from egodary.core import rule_matching

    rule_matching.load_cross_rules.cache_clear()


@lru_cache(maxsize=16)
def load_rules_bundle(slot: str) -> RulesBundle:
    return _load_slot(slot)


@lru_cache(maxsize=1)
def get_general_rules() -> RulesBundle:
    return load_rules_bundle(RULES_SLOT_GENERAL)


@lru_cache(maxsize=8)
def get_model_gen_rules(model_id: str) -> RulesBundle:
    return load_rules_bundle(model_slot(model_id))


def list_rules_slots() -> list[dict[str, Any]]:
    slots = [RULES_SLOT_GENERAL] + [model_slot(mid) for mid in MODEL_RULE_IDS]
    return [load_rules_bundle(slot).summary() for slot in slots]


def list_rule_profiles(slot: str) -> dict[str, Any]:
    parse_slot(slot)  # validate slot
    active = _load_active_profiles().get(slot, "default")
    items: list[dict[str, Any]] = [
        {
            "id": "default",
            "label": "Use default",
            "kind": "default",
            "active": active == "default",
            "deletable": False,
        }
    ]
    profile_dir = _profiles_dir(slot)
    if profile_dir.is_dir():
        for profile_id in sorted(_list_profile_ids(slot)):
            items.append(
                {
                    "id": profile_id,
                    "label": _profile_label(slot, profile_id),
                    "kind": "user",
                    "active": active == profile_id,
                    "path": str(_profile_path(slot, profile_id)),
                    "deletable": True,
                }
            )
    return {"slot": slot, "active_profile_id": active, "profiles": items}


def save_user_rules(
    slot: str,
    yaml_text: str,
    profile_id: str = "default",
    name: str | None = None,
) -> RulesBundle:
    parse_slot(slot)
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Rules file must be a YAML mapping at the root")

    selected_profile_id = profile_id
    if selected_profile_id == "default":
        cleaned_name = (name or "").strip()
        if not cleaned_name:
            raise ValueError("Rule name is required when creating a new profile")
        selected_profile_id = _unique_profile_id(slot, _slugify_profile_name(cleaned_name))
        _set_profile_meta(
            slot,
            selected_profile_id,
            {
                "name": cleaned_name,
                "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            },
        )
    else:
        if selected_profile_id in _RESERVED_PROFILE_IDS:
            raise ValueError("Profile id 'default' is reserved")
        if not _profile_path(slot, selected_profile_id).is_file():
            raise ValueError(f"User rule profile not found: {selected_profile_id}")
        cleaned_name = (name or "").strip()
        if cleaned_name:
            _set_profile_meta(slot, selected_profile_id, {"name": cleaned_name})

    path = _profile_path(slot, selected_profile_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml_text, encoding="utf-8")

    active = _load_active_profiles()
    active[slot] = selected_profile_id
    _save_active_profiles(active)
    invalidate_rules_cache()
    return load_rules_bundle(slot)


def reset_user_rules(slot: str) -> RulesBundle:
    kind, model_id = parse_slot(slot)
    # Legacy override file cleanup.
    legacy = _slot_path(kind, model_id, user=True)
    if legacy.is_file():
        legacy.unlink()
    active = _load_active_profiles()
    if slot in active:
        active.pop(slot, None)
        _save_active_profiles(active)
    invalidate_rules_cache()
    return load_rules_bundle(slot)


def select_rule_profile(slot: str, profile_id: str) -> RulesBundle:
    parse_slot(slot)
    if profile_id == "default":
        active = _load_active_profiles()
        if slot in active:
            active.pop(slot, None)
            _save_active_profiles(active)
        invalidate_rules_cache()
        return load_rules_bundle(slot)

    path = _profile_path(slot, profile_id)
    if not path.is_file():
        raise ValueError(f"User rule profile not found: {profile_id}")
    active = _load_active_profiles()
    active[slot] = profile_id
    _save_active_profiles(active)
    invalidate_rules_cache()
    return load_rules_bundle(slot)


def delete_rule_profile(slot: str, profile_id: str) -> RulesBundle:
    parse_slot(slot)
    if profile_id == "default":
        raise ValueError("Cannot delete default profile")

    path = _profile_path(slot, profile_id)
    if not path.is_file():
        raise ValueError(f"User rule profile not found: {profile_id}")
    path.unlink()
    _remove_profile_meta(slot, profile_id)

    active = _load_active_profiles()
    if active.get(slot) == profile_id:
        active.pop(slot, None)
    _save_active_profiles(active)

    invalidate_rules_cache()
    return load_rules_bundle(slot)


def read_rules_text(slot: str, profile_id: str | None = None) -> str:
    if profile_id and profile_id != "default":
        path = _profile_path(slot, profile_id)
        if path.is_file():
            return path.read_text(encoding="utf-8")
    bundle = load_rules_bundle(slot)
    if bundle.source_path:
        return Path(bundle.source_path).read_text(encoding="utf-8")
    return ""


def read_default_rules_text(slot: str) -> str:
    kind, model_id = parse_slot(slot)
    default_path = _slot_path(kind, model_id, user=False)
    if default_path.is_file():
        return default_path.read_text(encoding="utf-8")
    if kind == "general":
        legacy = _DEFAULT_CONTENT_DIR / "cross_rules.yaml"
        if legacy.is_file():
            return legacy.read_text(encoding="utf-8")
    return ""
