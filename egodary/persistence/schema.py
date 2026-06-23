"""Repository-style helper functions for persistence."""

from __future__ import annotations

import json

from egodary.core.llm_settings import LlmSettings
from egodary.core.models import TagItem
from egodary.core.runtime_registry import OverlaySource, RuntimeRegistry
from egodary.persistence.db import get_connection, init_db


def _parse_favorite_row(row) -> dict:
    item = dict(row)
    raw_settings = item.pop("settings_json", None)
    if raw_settings:
        try:
            item["generation_settings"] = json.loads(raw_settings)
        except json.JSONDecodeError:
            item["generation_settings"] = None
    else:
        item["generation_settings"] = None
    return item


def save_favorite(
    name: str,
    positive: str,
    negative: str | None,
    model_id: str,
    *,
    result_url: str | None = None,
    generation_settings: dict | None = None,
) -> int:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Favorite name is required")
    settings_json = (
        json.dumps(generation_settings, ensure_ascii=False) if generation_settings else None
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO favorites(name, positive, negative, model_id, result_url, settings_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (cleaned, positive, negative, model_id, result_url or None, settings_json),
    )
    conn.commit()
    row_id = int(cur.lastrowid)
    conn.close()
    return row_id


def list_favorites(limit: int = 50) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT id, name, positive, negative, model_id, result_url, settings_json, created_at
        FROM favorites ORDER BY id DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [_parse_favorite_row(r) for r in rows]


def get_favorite(favorite_id: int) -> dict | None:
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        """
        SELECT id, name, positive, negative, model_id, result_url, settings_json, created_at
        FROM favorites WHERE id = ?
        """,
        (favorite_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return _parse_favorite_row(row)


def delete_favorite(favorite_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM favorites WHERE id = ?", (favorite_id,))
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def update_favorite(
    favorite_id: int,
    name: str,
    positive: str,
    negative: str | None,
    model_id: str,
    *,
    result_url: str | None = None,
    generation_settings: dict | None = None,
) -> bool:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Favorite name is required")
    settings_json = (
        json.dumps(generation_settings, ensure_ascii=False) if generation_settings else None
    )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE favorites
        SET name = ?, positive = ?, negative = ?, model_id = ?, result_url = ?, settings_json = ?
        WHERE id = ?
        """,
        (cleaned, positive, negative, model_id, result_url or None, settings_json, favorite_id),
    )
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def save_generation_history(payload: dict, positive: str, negative: str | None, model_id: str) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO generation_history(positive, negative, model_id, payload_json) VALUES (?, ?, ?, ?)",
        (positive, negative, model_id, json.dumps(payload, ensure_ascii=False)),
    )
    conn.commit()
    row_id = int(cur.lastrowid)
    conn.close()
    return row_id


def record_unknown_tags(tokens: list[str], source_prompt: str | None = None) -> int:
    if not tokens:
        return 0
    conn = get_connection()
    cur = conn.cursor()
    recorded = 0
    for token in tokens:
        cleaned = token.strip()
        if not cleaned:
            continue
        cur.execute(
            """
            INSERT INTO unknown_tags(token, source_prompt, hit_count, status)
            VALUES (?, ?, 1, 'pending')
            ON CONFLICT(token) DO UPDATE SET
                hit_count = hit_count + 1,
                last_seen = CURRENT_TIMESTAMP,
                source_prompt = COALESCE(excluded.source_prompt, unknown_tags.source_prompt)
            """,
            (cleaned, source_prompt),
        )
        recorded += 1
    conn.commit()
    conn.close()
    return recorded


def list_unknown_tags(status: str = "pending", limit: int = 50) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT id, token, source_prompt, hit_count, status,
               suggested_category, suggested_subgroup, suggested_subcategory, resolution_status, notes,
               first_seen, last_seen
        FROM unknown_tags
        WHERE status = ?
        ORDER BY hit_count DESC, last_seen DESC
        LIMIT ?
        """,
        (status, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_unknown_tag(
    tag_id: int,
    *,
    status: str | None = None,
    suggested_category: str | None = None,
    suggested_subgroup: str | None = None,
    suggested_subcategory: str | None = None,
    resolution_status: str | None = None,
    notes: str | None = None,
) -> bool:
    fields: list[str] = []
    values: list[object] = []
    if status is not None:
        fields.append("status = ?")
        values.append(status)
    if suggested_category is not None:
        fields.append("suggested_category = ?")
        values.append(suggested_category)
    if suggested_subgroup is not None:
        fields.append("suggested_subgroup = ?")
        values.append(suggested_subgroup)
    if suggested_subcategory is not None:
        fields.append("suggested_subcategory = ?")
        values.append(suggested_subcategory)
    if resolution_status is not None:
        fields.append("resolution_status = ?")
        values.append(resolution_status)
    if notes is not None:
        fields.append("notes = ?")
        values.append(notes)
    if not fields:
        return False
    values.append(tag_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE unknown_tags SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def update_unknown_tag_by_token(
    token: str,
    *,
    status: str | None = None,
    suggested_category: str | None = None,
    suggested_subgroup: str | None = None,
    suggested_subcategory: str | None = None,
    resolution_status: str | None = None,
    notes: str | None = None,
) -> bool:
    fields: list[str] = []
    values: list[object] = []
    if status is not None:
        fields.append("status = ?")
        values.append(status)
    if suggested_category is not None:
        fields.append("suggested_category = ?")
        values.append(suggested_category)
    if suggested_subgroup is not None:
        fields.append("suggested_subgroup = ?")
        values.append(suggested_subgroup)
    if suggested_subcategory is not None:
        fields.append("suggested_subcategory = ?")
        values.append(suggested_subcategory)
    if resolution_status is not None:
        fields.append("resolution_status = ?")
        values.append(resolution_status)
    if notes is not None:
        fields.append("notes = ?")
        values.append(notes)
    if not fields:
        return False
    values.append(token.strip())
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE unknown_tags SET {', '.join(fields)} WHERE token = ?", values)
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def _character_preset_field_count(payload: dict) -> int:
    count = 0
    character = payload.get("character") or {}
    for key, val in character.items():
        if key == "body_details":
            count += len(val or [])
        elif val:
            count += 1
    face = payload.get("face") or {}
    count += sum(1 for val in face.values() if val)
    hair = (payload.get("appearance") or {}).get("hair") or ""
    hair_color = (payload.get("appearance") or {}).get("hair_color") or ""
    if hair:
        count += 1
    if hair_color:
        count += 1
    return count


def save_character_preset(name: str, payload: dict) -> int:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Character preset name is required")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO character_presets(name, payload_json) VALUES (?, ?)",
        (cleaned, json.dumps(payload, ensure_ascii=False)),
    )
    conn.commit()
    row_id = int(cur.lastrowid)
    conn.close()
    return row_id


def list_character_presets(limit: int = 50) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT id, name, payload_json, created_at FROM character_presets ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    result: list[dict] = []
    for row in rows:
        item = dict(row)
        try:
            payload = json.loads(item.pop("payload_json") or "{}")
        except json.JSONDecodeError:
            payload = {}
        item["field_count"] = _character_preset_field_count(payload)
        result.append(item)
    return result


def get_character_preset(preset_id: int) -> dict | None:
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, name, payload_json, created_at FROM character_presets WHERE id = ?",
        (preset_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    item = dict(row)
    item["payload"] = json.loads(item.pop("payload_json") or "{}")
    return item


def delete_character_preset(preset_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM character_presets WHERE id = ?", (preset_id,))
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def update_character_preset(preset_id: int, name: str) -> bool:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Character preset name is required")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE character_presets SET name = ? WHERE id = ?",
        (cleaned, preset_id),
    )
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


ADVANCED_TODO_KEY = "advanced_todo"
VALID_TODO_PRIORITIES = frozenset({"low", "medium", "high"})


def get_advanced_todo() -> dict:
    raw = get_app_setting(ADVANCED_TODO_KEY)
    if not raw or not isinstance(raw.get("items"), list):
        return {"items": []}
    items = []
    for row in raw["items"]:
        if not isinstance(row, dict):
            continue
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        priority = str(row.get("priority") or "medium").lower()
        if priority not in VALID_TODO_PRIORITIES:
            priority = "medium"
        due_date = row.get("due_date")
        if due_date is not None:
            due_date = str(due_date).strip() or None
        items.append(
            {
                "id": str(row.get("id") or ""),
                "text": text,
                "done": bool(row.get("done")),
                "priority": priority,
                "due_date": due_date,
                "sort_order": int(row.get("sort_order") or 0),
                "created_at": str(row.get("created_at") or ""),
            }
        )
    items.sort(key=lambda row: (row.get("sort_order", 0), row.get("created_at", "")))
    return {"items": items}


def save_advanced_todo(payload: dict) -> dict:
    items_in = payload.get("items") if isinstance(payload, dict) else []
    if not isinstance(items_in, list):
        raise ValueError("items must be a list")
    cleaned: list[dict] = []
    for index, row in enumerate(items_in):
        if not isinstance(row, dict):
            continue
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        priority = str(row.get("priority") or "medium").lower()
        if priority not in VALID_TODO_PRIORITIES:
            priority = "medium"
        due_date = row.get("due_date")
        if due_date is not None:
            due_date = str(due_date).strip() or None
        cleaned.append(
            {
                "id": str(row.get("id") or f"todo_{index}"),
                "text": text,
                "done": bool(row.get("done")),
                "priority": priority,
                "due_date": due_date,
                "sort_order": int(row.get("sort_order") if row.get("sort_order") is not None else index),
                "created_at": str(row.get("created_at") or ""),
            }
        )
    result = {"items": cleaned}
    save_app_setting(ADVANCED_TODO_KEY, result)
    return result


def _user_preset_field_count(payload: dict) -> int:
    return sum(1 for val in (payload or {}).values() if val)


def save_user_preset(scope: str, name: str, payload: dict, *, hint: str | None = None) -> int:
    cleaned_scope = scope.strip()
    cleaned_name = name.strip()
    if not cleaned_scope:
        raise ValueError("Preset scope is required")
    if not cleaned_name:
        raise ValueError("Preset name is required")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO user_presets(scope, name, payload_json, hint)
        VALUES (?, ?, ?, ?)
        """,
        (cleaned_scope, cleaned_name, json.dumps(payload, ensure_ascii=False), hint or None),
    )
    conn.commit()
    row_id = int(cur.lastrowid)
    conn.close()
    return row_id


def list_user_presets(scope: str, limit: int = 100) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT id, scope, name, payload_json, hint, created_at, updated_at
        FROM user_presets
        WHERE scope = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (scope.strip(), limit),
    ).fetchall()
    conn.close()
    result: list[dict] = []
    for row in rows:
        item = dict(row)
        try:
            payload = json.loads(item.pop("payload_json") or "{}")
        except json.JSONDecodeError:
            payload = {}
        item["payload"] = payload
        item["field_count"] = _user_preset_field_count(payload)
        result.append(item)
    return result


def get_user_preset(preset_id: int) -> dict | None:
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        """
        SELECT id, scope, name, payload_json, hint, created_at, updated_at
        FROM user_presets WHERE id = ?
        """,
        (preset_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    item = dict(row)
    item["payload"] = json.loads(item.pop("payload_json") or "{}")
    item["field_count"] = _user_preset_field_count(item["payload"])
    return item


def update_user_preset(
    preset_id: int,
    *,
    name: str | None = None,
    payload: dict | None = None,
    hint: str | None = None,
) -> bool:
    fields: list[str] = []
    values: list[object] = []
    if name is not None:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Preset name is required")
        fields.append("name = ?")
        values.append(cleaned)
    if payload is not None:
        fields.append("payload_json = ?")
        values.append(json.dumps(payload, ensure_ascii=False))
    if hint is not None:
        fields.append("hint = ?")
        values.append(hint or None)
    if not fields:
        return False
    fields.append("updated_at = CURRENT_TIMESTAMP")
    values.append(preset_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE user_presets SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def delete_user_preset(preset_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM user_presets WHERE id = ?", (preset_id,))
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def save_runtime_tag_items(registry: RuntimeRegistry) -> int:
    conn = get_connection()
    cur = conn.cursor()
    saved = 0
    for category_id, item, meta in registry.list_overlay_items():
        cur.execute(
            """
            INSERT INTO runtime_tag_items(category_id, item_id, source, item_json, original_phrase, status)
            VALUES (?, ?, ?, ?, ?, 'active')
            ON CONFLICT(category_id, item_id) DO UPDATE SET
                source = excluded.source,
                item_json = excluded.item_json,
                original_phrase = excluded.original_phrase,
                status = 'active'
            """,
            (
                category_id,
                item.id,
                meta.source,
                json.dumps(item.model_dump(), ensure_ascii=False),
                meta.original_phrase,
            ),
        )
        saved += 1
    conn.commit()
    conn.close()
    return saved


def save_runtime_tag_item(
    category_id: str,
    item: TagItem,
    *,
    source: OverlaySource = "user",
    original_phrase: str | None = None,
) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO runtime_tag_items(category_id, item_id, source, item_json, original_phrase, status)
        VALUES (?, ?, ?, ?, ?, 'active')
        ON CONFLICT(category_id, item_id) DO UPDATE SET
            source = excluded.source,
            item_json = excluded.item_json,
            original_phrase = excluded.original_phrase,
            status = 'active'
        """,
        (
            category_id,
            item.id,
            source,
            json.dumps(item.model_dump(), ensure_ascii=False),
            original_phrase,
        ),
    )
    conn.commit()
    conn.close()


def update_runtime_tag_item(
    category_id: str,
    item_id: str,
    item: TagItem,
    *,
    source: OverlaySource = "user",
    original_phrase: str | None = None,
) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE runtime_tag_items
        SET source = ?, item_json = ?, original_phrase = ?, status = 'active'
        WHERE category_id = ? AND item_id = ?
        """,
        (
            source,
            json.dumps(item.model_dump(), ensure_ascii=False),
            original_phrase,
            category_id,
            item_id,
        ),
    )
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def move_runtime_tag_item(
    *,
    from_category_id: str,
    to_category_id: str,
    item: TagItem,
    source: OverlaySource = "user",
    original_phrase: str | None = None,
) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM runtime_tag_items WHERE category_id = ? AND item_id = ?",
        (from_category_id, item.id),
    )
    cur.execute(
        """
        INSERT INTO runtime_tag_items(category_id, item_id, source, item_json, original_phrase, status)
        VALUES (?, ?, ?, ?, ?, 'active')
        ON CONFLICT(category_id, item_id) DO UPDATE SET
            source = excluded.source,
            item_json = excluded.item_json,
            original_phrase = excluded.original_phrase,
            status = 'active'
        """,
        (
            to_category_id,
            item.id,
            source,
            json.dumps(item.model_dump(), ensure_ascii=False),
            original_phrase,
        ),
    )
    conn.commit()
    conn.close()


def set_runtime_tag_item_status(category_id: str, item_id: str, status: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE runtime_tag_items SET status = ? WHERE category_id = ? AND item_id = ?",
        (status, category_id, item_id),
    )
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def load_runtime_tag_items_into_registry(
    registry: RuntimeRegistry,
    *,
    status: str = "active",
) -> int:
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT category_id, item_id, source, item_json, original_phrase
        FROM runtime_tag_items
        WHERE status = ?
        """,
        (status,),
    ).fetchall()
    conn.close()
    loaded = 0
    for row in rows:
        try:
            item = TagItem.model_validate(json.loads(row["item_json"]))
        except (json.JSONDecodeError, ValueError):
            continue
        source: OverlaySource = row["source"] if row["source"] in ("import", "user", "manual", "wildcard") else "import"
        registry.add_item(
            row["category_id"],
            item,
            source=source,
            on_conflict="skip",
            original_phrase=row["original_phrase"],
        )
        loaded += 1
    return loaded


def list_runtime_tag_items(limit: int = 200) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT id, category_id, item_id, source, item_json, original_phrase, status, created_at
        FROM runtime_tag_items
        WHERE status = 'active'
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    result: list[dict] = []
    for row in rows:
        item = dict(row)
        try:
            item["item"] = json.loads(item.pop("item_json"))
        except json.JSONDecodeError:
            item["item"] = {}
        result.append(item)
    return result


def migrate_runtime_subgroup_to_subcategory(*, status: str = "active") -> dict[str, int]:
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT id, item_json FROM runtime_tag_items WHERE status = ?",
        (status,),
    ).fetchall()
    scanned = 0
    migrated = 0
    for row in rows:
        scanned += 1
        try:
            payload = json.loads(row["item_json"])
            item = TagItem.model_validate(payload)
        except (json.JSONDecodeError, ValueError):
            continue
        meta = item.meta or {}
        subgroup = str(meta.get("subgroup") or "").strip()
        subcategory = str(meta.get("subcategory_id") or "").strip()
        changed = False
        if subgroup and not subcategory:
            meta["subcategory_id"] = subgroup
            changed = True
        if subcategory and not subgroup:
            meta["subgroup"] = subcategory
            changed = True
        if "normalized_name" not in meta or not str(meta.get("normalized_name") or "").strip():
            meta["normalized_name"] = item.label.strip().lower()
            changed = True
        if "aliases" not in meta or not isinstance(meta.get("aliases"), list):
            meta["aliases"] = []
            changed = True
        if "is_active" not in meta:
            meta["is_active"] = True
            changed = True
        if not changed:
            continue
        item.meta = meta
        cur.execute(
            "UPDATE runtime_tag_items SET item_json = ? WHERE id = ?",
            (json.dumps(item.model_dump(), ensure_ascii=False), row["id"]),
        )
        migrated += 1
    conn.commit()
    conn.close()
    return {"scanned": scanned, "migrated": migrated}


def rollback_runtime_subcategory_to_subgroup(*, status: str = "active") -> dict[str, int]:
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT id, item_json FROM runtime_tag_items WHERE status = ?",
        (status,),
    ).fetchall()
    scanned = 0
    rolled_back = 0
    for row in rows:
        scanned += 1
        try:
            payload = json.loads(row["item_json"])
            item = TagItem.model_validate(payload)
        except (json.JSONDecodeError, ValueError):
            continue
        meta = item.meta or {}
        subcategory = str(meta.get("subcategory_id") or "").strip()
        subgroup = str(meta.get("subgroup") or "").strip()
        changed = False
        if subcategory and not subgroup:
            meta["subgroup"] = subcategory
            changed = True
        if "subcategory_id" in meta:
            del meta["subcategory_id"]
            changed = True
        if not changed:
            continue
        item.meta = meta
        cur.execute(
            "UPDATE runtime_tag_items SET item_json = ? WHERE id = ?",
            (json.dumps(item.model_dump(), ensure_ascii=False), row["id"]),
        )
        rolled_back += 1
    conn.commit()
    conn.close()
    return {"scanned": scanned, "rolled_back": rolled_back}


def get_app_setting(key: str) -> dict | None:
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute("SELECT value_json FROM app_settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    if not row:
        return None
    try:
        return json.loads(row["value_json"])
    except json.JSONDecodeError:
        return None


def save_app_setting(key: str, value: dict) -> None:
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO app_settings(key, value_json, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            value_json = excluded.value_json,
            updated_at = CURRENT_TIMESTAMP
        """,
        (key, json.dumps(value, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()


def load_llm_settings() -> LlmSettings:
    raw = get_app_setting("llm")
    if not raw:
        return LlmSettings()
    try:
        return LlmSettings.model_validate(raw)
    except Exception:
        return LlmSettings()


def save_llm_settings(settings: LlmSettings) -> None:
    save_app_setting("llm", settings.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Wildcards
# ---------------------------------------------------------------------------


def create_wildcard(
    *,
    filename: str,
    label: str,
    target_category: str,
    target_subgroup: str,
    raw_text: str,
    items: list[tuple[str, str]],  # (item_id, label) pairs in file order
) -> int:
    """Insert a new wildcard file with its parsed line items.

    Returns the new wildcard id.
    """
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO wildcards(filename, label, target_category, target_subgroup, enabled, raw_text, item_count)
        VALUES (?, ?, ?, ?, 1, ?, ?)
        """,
        (filename, label, target_category, target_subgroup, raw_text, len(items)),
    )
    wildcard_id = cur.lastrowid
    cur.executemany(
        "INSERT INTO wildcard_items(wildcard_id, item_id, label, enabled) VALUES (?, ?, ?, 1)",
        [(wildcard_id, item_id, item_label) for item_id, item_label in items],
    )
    conn.commit()
    conn.close()
    return wildcard_id


def list_wildcards() -> list[dict]:
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT id, filename, label, target_category, target_subgroup, enabled,
               item_count, created_at, updated_at
        FROM wildcards
        ORDER BY created_at DESC
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_wildcard(wildcard_id: int) -> dict | None:
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM wildcards WHERE id = ?", (wildcard_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_wildcard_items(wildcard_id: int) -> list[dict]:
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT id, item_id, label, enabled FROM wildcard_items WHERE wildcard_id = ? ORDER BY id",
        (wildcard_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def set_wildcard_enabled(wildcard_id: int, enabled: bool) -> bool:
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE wildcards SET enabled = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (1 if enabled else 0, wildcard_id),
    )
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def set_wildcard_item_enabled(wildcard_id: int, item_id: str, enabled: bool) -> bool:
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE wildcard_items SET enabled = ? WHERE wildcard_id = ? AND item_id = ?",
        (1 if enabled else 0, wildcard_id, item_id),
    )
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def delete_wildcard(wildcard_id: int) -> bool:
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM wildcard_items WHERE wildcard_id = ?", (wildcard_id,))
    cur.execute("DELETE FROM wildcards WHERE id = ?", (wildcard_id,))
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def load_wildcards_into_registry(registry: RuntimeRegistry) -> int:
    """Load all enabled wildcards (and their enabled line items) into the
    runtime overlay registry as TagItems under their target category.

    Item ids are namespaced with the owning wildcard's row id
    (``wc{wildcard_id}_{item_id}``) so that two different uploaded files
    can never collide on id — e.g. two files both containing a line that
    slugifies to "long_bangs" used to mean the second one was silently
    dropped by the registry's add_item(on_conflict="skip"), making it look
    like tags (or even a whole file's worth of overlapping tags) had
    "disappeared" until the colliding file was deleted. The wildcard's own
    item_id in the wildcard_items table (used for the per-line enable
    checkbox) is unaffected — only the id used inside the live tag
    registry is namespaced.
    """
    from egodary.core.wildcards import build_tag_item

    init_db()
    conn = get_connection()
    cur = conn.cursor()
    wildcard_rows = cur.execute(
        "SELECT id, target_category, target_subgroup FROM wildcards WHERE enabled = 1"
    ).fetchall()
    loaded = 0
    for wrow in wildcard_rows:
        item_rows = cur.execute(
            "SELECT item_id, label FROM wildcard_items WHERE wildcard_id = ? AND enabled = 1",
            (wrow["id"],),
        ).fetchall()
        for irow in item_rows:
            registry_item_id = f"wc{wrow['id']}_{irow['item_id']}"
            tag_item = build_tag_item(irow["label"], registry_item_id, subgroup=wrow["target_subgroup"])
            registry.add_item(
                wrow["target_category"],
                tag_item,
                source="wildcard",
                on_conflict="skip",
            )
            loaded += 1
    conn.close()
    return loaded


# ---------------------------------------------------------------------------
# Generation history
# ---------------------------------------------------------------------------


def list_generation_history(
    limit: int = 50,
    model_id: str | None = None,
) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    if model_id:
        rows = cur.execute(
            """
            SELECT id, positive, negative, model_id, payload_json, created_at
            FROM generation_history
            WHERE model_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (model_id, limit),
        ).fetchall()
    else:
        rows = cur.execute(
            """
            SELECT id, positive, negative, model_id, payload_json, created_at
            FROM generation_history
            ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    conn.close()
    result = []
    for row in rows:
        item = dict(row)
        raw = item.pop("payload_json", None)
        if raw:
            try:
                item["payload"] = json.loads(raw)
            except json.JSONDecodeError:
                item["payload"] = None
        else:
            item["payload"] = None
        result.append(item)
    return result


def delete_generation_history_entry(entry_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM generation_history WHERE id = ?", (entry_id,))
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def clear_generation_history(model_id: str | None = None) -> int:
    conn = get_connection()
    cur = conn.cursor()
    if model_id:
        cur.execute("DELETE FROM generation_history WHERE model_id = ?", (model_id,))
    else:
        cur.execute("DELETE FROM generation_history")
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    return deleted


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


def save_session(name: str, state: dict) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO sessions(name, state_json)
        VALUES (?, ?)
        """,
        (name.strip(), json.dumps(state, ensure_ascii=False)),
    )
    conn.commit()
    row_id = int(cur.lastrowid)
    conn.close()
    return row_id


def list_sessions() -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT id, name, created_at, updated_at FROM sessions ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session(session_id: int) -> dict | None:
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, name, state_json, created_at, updated_at FROM sessions WHERE id = ?",
        (session_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    item = dict(row)
    raw = item.pop("state_json", None)
    try:
        item["state"] = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        item["state"] = {}
    return item


def update_session_name(session_id: int, name: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE sessions SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (name.strip(), session_id),
    )
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def delete_session(session_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


# ---------------------------------------------------------------------------
# Forge settings
# ---------------------------------------------------------------------------


FORGE_SETTINGS_KEY = "forge"


def load_forge_settings() -> dict:
    raw = get_app_setting(FORGE_SETTINGS_KEY)
    defaults: dict = {
        "enabled": False,
        "base_url": "http://127.0.0.1:7860",
        "timeout": 10.0,
        "default_steps": 20,
        "default_cfg": 7.0,
        "default_sampler": "DPM++ 2M",
        "default_scheduler": "Karras",
        "default_width": 832,
        "default_height": 1216,
        "default_checkpoint": "",
        "hires_enabled": False,
        "hires_scale": 1.5,
        "hires_upscaler": "4x-UltraSharp",
        "hires_steps": 15,
        "hires_denoising": 0.45,
        "save_images": False,
    }
    if not raw:
        return defaults
    defaults.update(raw)
    return defaults


def save_forge_settings(settings: dict) -> None:
    save_app_setting(FORGE_SETTINGS_KEY, settings)

