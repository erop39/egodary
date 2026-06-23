"""Wildcards — пользовательские текстовые списки тегов, привязанные к
существующей категории/подгруппе генератора (или к новой подгруппе внутри
существующей категории).

Пользователь загружает .txt файл со строками вида:

    Long layered hair with curtain bangs
    Textured lob with curtain bangs
    Blunt cut bob
    ...

Каждая непустая строка (после очистки от маркеров списка `*`/`-`/`•`)
становится отдельным TagItem: id и алиас генерируются автоматически из
текста строки (slug), а сама строка используется как готовая фраза тега
для всех трёх моделей (Illustrious/Anima/Z-Image Turbo) — естественный
текст одинаково хорошо ложится во все три формата.

Хранение в БД: таблица `wildcards` — один файл (с привязкой к категории +
подгруппе, общим enabled-флагом), таблица `wildcard_items` — построчные
записи с собственным id/label/enabled (чекбокс на каждую строку).
Сами теги попадают в RuntimeRegistry overlay (как и runtime tag items из
prompt import) с `source="wildcard"`, поэтому генератор видит их как
обычные теги выбранной категории/подгруппы без какой-либо отдельной логики
в pipeline.
"""

from __future__ import annotations

import re

from egodary.core.models import TagItem

_BULLET_PREFIX_RE = re.compile(r"^\s*[\*\-•\u2022]\s*")
_NON_WORD_RE = re.compile(r"[^a-z0-9]+")


def slugify(label: str) -> str:
    """Преобразует произвольную строку в snake_case id."""
    text = label.lower().strip()
    text = text.replace("&", " and ")
    text = _NON_WORD_RE.sub("_", text)
    text = text.strip("_")
    text = re.sub(r"_+", "_", text)
    return text or "item"


def parse_wildcard_lines(raw_text: str) -> list[str]:
    """Разбивает сырой текст файла на список непустых строк-фраз,
    удаляя маркеры списка (*, -, •) и пустые строки."""
    lines: list[str] = []
    for raw_line in raw_text.splitlines():
        line = _BULLET_PREFIX_RE.sub("", raw_line).strip()
        if line:
            lines.append(line)
    return lines


def make_item_id(label: str, used_ids: set[str]) -> str:
    """Генерирует уникальный id для строки внутри набора уже использованных id."""
    base = slugify(label)
    if base not in used_ids:
        return base
    suffix = 2
    while f"{base}_{suffix}" in used_ids:
        suffix += 1
    return f"{base}_{suffix}"


def build_tag_item(label: str, item_id: str, *, subgroup: str | None = None) -> TagItem:
    """Строит TagItem из строки wildcard-файла.

    Фраза используется как есть для всех целевых моделей — это естественный
    текст, который одинаково хорошо работает в danbooru-стиле (Illustrious),
    блочном формате (Anima) и natural language (Z-Image Turbo).
    """
    meta: dict = {"source": "wildcard"}
    if subgroup:
        meta["subcategory_id"] = subgroup
        meta["subgroup"] = subgroup
    return TagItem(
        id=item_id,
        label=label,
        tags={
            "illustrious": label.lower(),
            "anima": f"{label.lower()}, styled outfit",
            "zimage_turbo": label.lower(),
        },
        meta=meta,
    )


def parse_wildcard_file(
    raw_text: str,
    *,
    subgroup: str | None = None,
) -> list[tuple[str, TagItem]]:
    """Парсит сырой текст файла в список (label, TagItem) с уникальными id."""
    lines = parse_wildcard_lines(raw_text)
    used_ids: set[str] = set()
    result: list[tuple[str, TagItem]] = []
    for line in lines:
        item_id = make_item_id(line, used_ids)
        used_ids.add(item_id)
        result.append((line, build_tag_item(line, item_id, subgroup=subgroup)))
    return result
