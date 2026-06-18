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
        source: OverlaySource = row["source"] if row["source"] in ("import", "user", "manual") else "import"
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

