"""FETISH_EXTERNAL_SKIP — skip fetish tags already expressed elsewhere in state."""

from __future__ import annotations

from pathlib import Path

import yaml

_SKIP_RULES: dict[str, list[dict]] | None = None


def _rules_path() -> Path:
    return Path(__file__).resolve().parents[1] / "content" / "fetish_pack" / "external_skip.yaml"


def load_external_skip_rules() -> dict[str, list[dict]]:
    global _SKIP_RULES
    if _SKIP_RULES is not None:
        return _SKIP_RULES
    path = _rules_path()
    if not path.is_file():
        _SKIP_RULES = {}
        return _SKIP_RULES
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    _SKIP_RULES = data.get("rules", {})
    return _SKIP_RULES


def _get_field(state: object, field: str):
    if field == "leg_detail_focus":
        return getattr(state, "leg_detail_focus", False)
    parts = field.split(".")
    cur = state
    for part in parts:
        cur = getattr(cur, part, None)
        if cur is None:
            return None
    return cur


def should_skip_fetish_item(state: object, item_id: str) -> bool:
    rules = load_external_skip_rules().get(item_id, [])
    for rule in rules:
        field = rule.get("field", "")
        value = _get_field(state, field)
        if "equals" in rule:
            expected = rule["equals"]
            if isinstance(expected, bool):
                if bool(value) != expected:
                    continue
            elif str(value).lower() != str(expected).lower():
                continue
        if "not_equals" in rule and str(value).lower() == str(rule["not_equals"]).lower():
            continue
        if "includes" in rule:
            needle = rule["includes"]
            if isinstance(value, list):
                if needle not in value:
                    continue
            elif not (isinstance(value, str) and needle in value):
                continue
        return True
    return False
