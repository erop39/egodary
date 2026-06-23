# Wildcards → настоящий плагин

> Статус: **отложено** · Приоритет: средний
> Текущее поведение: wildcards — встроенная безусловная часть ядра, не управляется через Plugins panel.
> Цель: включаем плагин → появляется вкладка Wildcards и весь функционал. Выключаем → генератор работает без каких-либо следов wildcards.

---

## Почему сейчас это не плагин

### 1. Вкладка — hardcoded в HTML

```html
<!-- index.html — всегда видна, без каких-либо условий -->
<button class="nav-item" data-tab="wildcards">🃏 Wildcards</button>
<section class="panel" data-panel="wildcards">...</section>
```

### 2. Загрузка в registry — безусловная

```python
# app.py — вызывается при каждом get_runtime_registry(), всегда
load_wildcards_into_registry(_runtime_registry)
```

### 3. API-эндпоинты — hardcoded в main.py

Всегда активны, без проверки флага плагина:
- `GET /api/wildcards`
- `GET /api/wildcards/by-category/{category_id}`
- `GET /api/wildcards/{wildcard_id}`
- `POST /api/wildcards/preview`
- `POST /api/wildcards`
- `POST /api/wildcards/{wildcard_id}/toggle`
- `POST /api/wildcards/{wildcard_id}/items/{item_id}/toggle`
- `DELETE /api/wildcards/{wildcard_id}`

### 4. Инъекция в дерево тегов — безусловная

```js
// app.js — injectWildcardLeaves() вызывается при рендере любой панели
```

### 5. В Plugins panel wildcards нет совсем

Нет `manifest.toml` → `GET /api/plugins` о wildcards ничего не знает.

---

## Целевое поведение

| Состояние плагина | Поведение |
|---|---|
| **Включён** | Вкладка «🃏 Wildcards» видна в nav; все `/api/wildcards/*` работают; `injectWildcardLeaves()` добавляет листья в деревья; wildcards грузятся в registry |
| **Выключен** | Вкладка скрыта; `/api/wildcards/*` возвращают 404 (или пустой список с `"disabled": true`); `injectWildcardLeaves()` не вызывается; `load_wildcards_into_registry` пропускается; генератор работает как будто wildcards не существует |

---

## Что нужно изменить

### Уровень 1 — Plugin manifest

Создать `egodary/content/wildcards_pack/manifest.toml`:

```toml
[plugin]
id = "wildcards"
name = "Wildcards"
version = "1.0.0"
kind = "feature_pack"          # новый kind, или переиспользовать "ui_extension"
description = "Пользовательские текстовые списки тегов — привязка к категории/подгруппе."
requires_core = ">=0.1.0"
enabled_by_default = true      # включён сразу после установки
```

Либо добавить новый `PluginKind.FEATURE_PACK` в `plugins/base.py` и `plugins/manifest.py`,
либо переиспользовать `ui_extension` с флагом `has_ui = true`.

### Уровень 2 — Plugin persistence

Добавить в `app_settings` (или отдельную таблицу `plugin_states`) хранение флага `enabled`
для builtin-плагинов (dropin-плагины уже хранят это в `plugins_user_enabled` в `app_settings`).

`GET /api/plugins` должен возвращать wildcards в списке, с `enabled: true/false` и `source: "builtin"`.

### Уровень 3 — Backend guard

```python
# app.py
def _wildcards_enabled() -> bool:
    return get_plugin_enabled("wildcards")  # читает из app_settings

def get_runtime_registry(...):
    ...
    if _wildcards_enabled():
        load_wildcards_into_registry(_runtime_registry)
    ...
```

```python
# api/main.py — обернуть все /api/wildcards/* endpoints
def _require_wildcards():
    if not _wildcards_enabled():
        raise HTTPException(404, detail="Wildcards plugin is disabled")

@app.get("/api/wildcards")
def wildcards_list():
    _require_wildcards()
    ...
```

### Уровень 4 — Frontend: условный рендер вкладки

```js
// app.js — при инициализации
async function init() {
    const pluginsData = await api("/plugins");
    const wildcardsPlugin = pluginsData.plugins.find(p => p.id === "wildcards");
    const wildcardsEnabled = wildcardsPlugin?.enabled ?? true;

    // Скрыть/показать nav tab и panel
    document.querySelector('[data-tab="wildcards"]')
        ?.classList.toggle("hidden", !wildcardsEnabled);
    document.querySelector('[data-panel="wildcards"]')
        ?.classList.toggle("hidden", !wildcardsEnabled);

    window.__wildcardsEnabled = wildcardsEnabled;
    ...
}
```

### Уровень 5 — Frontend: условный `injectWildcardLeaves`

```js
function injectWildcardLeaves(nodes) {
    if (!window.__wildcardsEnabled) return nodes;
    // ... существующая логика ...
}
```

То же для `loadWildcardsIndex()`, `appendWildcardsSection()`,
`invalidateWildcardsByCategoryCache()` — проверять флаг перед вызовом.

### Уровень 6 — Plugins panel UI

При toggle wildcards в Plugins panel:
- POST `/api/plugins/wildcards/enable` или `/disable`
- Показать toast «Перезагрузите страницу для применения изменений» (tab visibility меняется через reload, не hot)
- Или: hot-apply через `location.reload()` после toggle (самый простой вариант)

---

## Порядок реализации

1. `plugins/base.py` + `plugins/manifest.py` — добавить `PluginKind.FEATURE_PACK`
2. `egodary/content/wildcards_pack/manifest.toml` — создать манифест
3. `persistence/db.py` + `persistence/schema.py` — хранение enabled-флага для builtin плагинов
4. `app.py` — обернуть `load_wildcards_into_registry` в guard
5. `api/main.py` — добавить `_require_wildcards()` guard на все endpoints; расширить `GET /api/plugins` для builtin плагинов
6. `app.js` — условный рендер tab/panel в `init()`; guard в `injectWildcardLeaves` и связанных функциях
7. Тесты: включён/выключен → генерация без wildcards-тегов, API возвращает 404

---

## Что НЕ меняется

- Логика самих wildcards (парсинг, хранение в БД, привязка к категории/подгруппе) — без изменений
- Схема БД таблицы wildcards — без изменений
- Поведение когда плагин включён — полностью идентично текущему

---

## Затронутые файлы

| Файл | Изменение |
|---|---|
| `plugins/base.py` | + `FEATURE_PACK` в `PluginKind` |
| `plugins/manifest.py` | поддержка нового kind |
| `plugins/loader.py` | загрузка builtin feature_pack плагинов |
| `egodary/content/wildcards_pack/manifest.toml` | **создать** |
| `persistence/db.py` | хранение enabled-флага builtin плагинов |
| `persistence/schema.py` | `get_plugin_enabled()`, `set_plugin_enabled()` |
| `app.py` | guard в `get_runtime_registry()` |
| `api/main.py` | `_require_wildcards()` + builtin plugins в `GET /api/plugins` + `POST /api/plugins/{id}/enable\|disable` |
| `web/static/index.html` | убрать hardcoded wildcards tab (сделать через JS) или добавить `hidden` по умолчанию |
| `web/static/js/app.js` | условный рендер tab/panel в `init()`, guards в wildcard-функциях |

---

## Out of scope

- Hot-swap без перезагрузки страницы (достаточно `location.reload()` после toggle)
- Другие builtin фичи как плагины (pose, character и т.д.) — отдельное решение
