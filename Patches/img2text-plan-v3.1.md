# img2text — план реализации v3.1

> Статус: **не начата** · Целевая версия: **0.2.1**
> Основан на v3 с правками по code-review (model_id, vision health, favorites фильтрация,
> draft auto-save, UX edge-cases и др.)

---

## Архитектура

```
Prompting → Img2Text card
┌─────────────────────────────────────────────┐
│  [Drop zone / image preview]  hint: WxH, KB │
│                                             │
│  [Anima] [Illustrious] [Z-Image Turbo]      │
│                                             │
│  Rule for Illustrious:                      │
│  ┌─────────────────────────────────────┐    │
│  │ textarea — одно правило вручную     │    │  ← auto-saved: localStorage + PUT debounce
│  └─────────────────────────────────────┘    │
│  [★ Save to favorites]                      │
│                                             │
│  — Saved rules (Illustrious) ─────────────  │
│    • "Detailed tags"   [Load] [✕]           │
│    • "Portrait focus"  [Load] [✕]           │
│    (последние 10, ссылка → Favorites tab)   │
│                                             │
│  [Additional notes — optional]              │
│  Vision model: llava:13b  (из настроек)     │
│  [☑ Use LLM]                                │
│  [Convert ▶]                                │
│                                             │
│  [Output prompt]  [Copy] [★ Save prompt]    │
└─────────────────────────────────────────────┘
```

---

## Ключевые решения (финальные)

| Решение | Выбор |
|---|---|
| Правила | 1 текстовое правило на модель (3 слота) |
| Model-id третьей модели | `zimage_turbo` (не `zit` — несовместимо с существующим кодом) |
| Draft | localStorage (мгновенно) + PUT debounce 2 s; без отдельной кнопки «Save draft» |
| Пустое правило | Разрешено — Convert работает с минимальным system prompt; ответ содержит `"rule_applied": false` |
| Vision model | Отдельное поле `vision_model` в `LlmSettings` (не путать с text `model`) |
| Health probe | Отдельный `check_vision_health()`: 1×1 px JPEG + `"Describe in one word"` — без `format:json` (vision-модели его игнорируют) |
| Транспорт | JSON + base64; client resize ≤ 1024 px long side, JPEG q=0.85; backend лимит 12 МБ (encoded) → 413 |
| rule_source | Передаётся клиентом в POST (`"draft" \| "favorite" \| "manual"`), эхоится в ответе |
| Favorites фильтрация | По верхнеуровневому `model_id` (SQL-столбец) + `kind = "img2text_rules"` в settings_json; `img2text_model` внутри generation_settings — **убрать** (дублирует model_id) |
| Inline список | Последние 10 по model + kind; ссылка на Favorites tab для остального |
| Load favorite с unsaved | confirm если `textarea.value !== draft[model]` |
| Cross-panel «Load in Img2Text» | `pendingImg2textLoad = { model_id, rule_text }` в глобальном state; применяется при открытии панели |
| Tag dedupe (Illustrious) | Exact match после trim+lowercase; первое вхождение; порядок сохраняется |
| Export | **Out of scope 0.2.1** |
| `vision_model_override` в POST | **Убрать** — UI не предоставляет это поле, лишняя путаница |

---

## Backend

### 1. `LlmSettings` — новые поля

```python
class LlmSettings(BaseModel):
    # ... существующие поля ...
    vision_model: str = ""           # пусто = vision недоступен
    vision_timeout: float = 60.0     # vision-модели медленнее
```

`LlmHealthReport` расширяется:

```python
class LlmHealthReport(BaseModel):
    # ... существующие поля ...
    vision_model: str | None = None
    vision_healthy: bool = False
    vision_error: str | None = None
```

---

### 2. `ollama.py` — новые функции

#### `_chat_vision(system, user, image_b64, *, settings) -> str | None`

```python
# Ключевые отличия от _chat():
# - НЕТ "format": "json" (vision-модели игнорируют или ломаются)
# - images: [image_b64] в user-сообщении
# - использует settings.vision_model и settings.vision_timeout
# - свой retry-цикл
payload = {
    "model": settings.vision_model,
    "messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": user, "images": [image_b64]},
    ],
    "stream": False,
    "options": {"temperature": settings.temperature, "top_p": settings.top_p},
    # НЕТ "format": "json"
}
```

#### `check_vision_health(settings, *, force) -> LlmHealthReport`

Probe:
- Image: `VISION_PROBE_IMAGE_B64` из `defaults.py` (1×1 px белый JPEG, ~300 байт)
- System: `"You are a vision assistant."`
- User: `"What color is this image? Reply with one word."` + images
- Healthy если ответ непустой и не содержит error-слов

---

### 3. Структура модуля

```
egodary/prompting/prompt_img2text/
├── __init__.py
├── defaults.py       # VISION_PROBE_IMAGE_B64, MODEL_PLACEHOLDERS, SYSTEM_PROMPT
├── rules.py          # load_draft() / save_draft() через app_settings
├── describe.py       # build_messages() + convert_image()
└── normalize.py      # dedupe_illustrious_tags()
```

#### `defaults.py`

```python
VISION_PROBE_IMAGE_B64 = "/9j/4AAQSkZJRgABAQEASABIAAD..."  # 1×1 white JPEG

SYSTEM_PROMPT = """You are a vision assistant that converts images into AI image generation prompts.
Output plain text only — no markdown, no explanations, no preamble.
Describe only what is visibly present in the image."""

MODEL_PLACEHOLDERS = {
    "anima": "Natural language blocks separated by newlines.\nExample: young woman, long dark hair...",
    "illustrious": "Comma-separated danbooru-style tags.\nExample: 1girl, long hair, black hair...",
    "zimage_turbo": "Short descriptive prose, 1-2 sentences.\nExample: A young woman with long dark hair...",
}

VALID_MODEL_IDS = {"anima", "illustrious", "zimage_turbo"}
```

#### `rules.py` — draft в app_settings

Ключ: `"img2text_rules_draft"`

```json
{
  "version": 1,
  "rules": {
    "anima": "",
    "illustrious": "",
    "zimage_turbo": ""
  },
  "updated_at": "2026-06-18T12:00:00Z"
}
```

`load_draft()` — читает из app_settings, мерджит с дефолтными пустыми строками (на случай если ключ отсутствует).
`save_draft(rules: dict)` — валидирует ключи (только `VALID_MODEL_IDS`), сохраняет.

#### `describe.py`

```python
def convert_image(
    *,
    image_base64: str,
    image_mime: str,
    model_id: str,
    rule_text: str,
    use_llm: bool,
    extra_instruction: str = "",
    rule_source: str = "manual",
) -> dict:
    # 1. Валидация image_mime (image/jpeg, image/png, image/webp)
    # 2. Валидация len(image_base64) <= 12_000_000 → 413
    # 3. Валидация model_id in VALID_MODEL_IDS
    # 4. Если not use_llm → вернуть {"prompt": "", "used_llm": False, ...}
    # 5. check_vision_health() → если не healthy → raise HTTP 400
    # 6. Построить user message:
    #      [Instruction]\n{rule_text или "(no rule)"}\n
    #      [Target model]\n{model_id}\n
    #      [Additional notes]\n{extra_instruction}
    # 7. _chat_vision(SYSTEM_PROMPT, user_message, image_base64)
    # 8. post-process:
    #      - strip() + убрать ```-фенсы
    #      - если illustrious: normalize.dedupe_illustrious_tags()
    # 9. Вернуть dict с prompt, model_id, used_llm, rule_applied, rule_source, image_meta, llm_status
```

#### `normalize.py`

```python
def dedupe_illustrious_tags(text: str) -> str:
    """Exact-match dedupe comma-separated tags.
    Rules:
    - split by comma, strip each tag
    - lowercase для сравнения, оригинальный регистр сохраняется
    - первое вхождение побеждает
    - пустые элементы удаляются
    - порядок сохраняется
    """
```

---

### 4. API endpoints

#### `GET /api/prompt/img2text/rules`

```json
{
  "rules": {
    "anima": "...",
    "illustrious": "...",
    "zimage_turbo": "..."
  },
  "updated_at": "2026-06-18T12:00:00Z",
  "placeholders": { ... }   // из defaults.py, для UI
}
```

#### `PUT /api/prompt/img2text/rules`

Request:
```json
{ "rules": { "anima": "...", "illustrious": "...", "zimage_turbo": "..." } }
```

Merge: обновляет только переданные ключи (partial update).

#### `POST /api/prompt/img2text`

Request:
```json
{
  "image_base64": "...",
  "image_mime": "image/jpeg",
  "model_id": "illustrious",
  "rule_text": "Comma-separated danbooru tags...",
  "rule_source": "draft",
  "use_llm": true,
  "extra_instruction": ""
}
```

Response:
```json
{
  "prompt": "1girl, long hair, ...",
  "model_id": "illustrious",
  "used_llm": true,
  "rule_applied": true,
  "rule_source": "draft",
  "llm_status": {
    "vision_model": "llava:13b",
    "vision_healthy": true,
    "latency_ms": 3200
  },
  "llm_error": null,
  "image_meta": { "bytes_received": 245000 }
}
```

Ошибки:
- 400 `"vision_model not configured"` — поле `vision_model` пустое в настройках
- 400 `"vision model unhealthy: ..."` — probe упал
- 400 `"unsupported image type"` — не jpeg/png/webp
- 413 `"image too large"` — > 12 МБ encoded
- 422 `"invalid model_id"` — не в VALID_MODEL_IDS

#### Расширение `GET /api/favorites`

Добавить query-параметры (опциональные):
```
GET /api/favorites?kind=img2text_rules&model_id=illustrious&limit=10
```

Реализация в `list_favorites(kind, model_id, limit)` — SQL-фильтрация:
- `model_id` уже в отдельном столбце → `WHERE model_id = ?`
- `kind` хранится в `settings_json` → `WHERE settings_json LIKE '%"kind": "img2text_rules"%'`
  (допустимо — поле маленькое, записей немного, индекс не нужен)

---

### 5. Favorites schema для img2text rules

```json
{
  "name": "Illustrious — portrait detail",
  "positive": "<текст правила>",
  "negative": null,
  "model_id": "illustrious",
  "generation_settings": {
    "kind": "img2text_rules"
  }
}
```

Изменения vs v3:
- ❌ убран `"img2text_model"` — дублировал `model_id`
- `"positive"` = текст правила (для совместимости с Favorites tab)
- `"kind": "img2text_rules"` — единственный маркер

---

## Frontend

### Новый state

```js
let activeImg2textModel = "illustrious";   // "anima" | "illustrious" | "zimage_turbo"
let img2textDraft = { anima: "", illustrious: "", zimage_turbo: "" };
let img2textFavoritesCache = [];           // фильтровано по activeImg2textModel
let img2textLastSavedDraft = null;         // для dirty-check перед Load
let pendingImg2textLoad = null;            // { model_id, rule_text } — cross-panel nav
```

### Draft auto-save (без кнопки)

```js
// При изменении textarea:
img2textDraft[activeImg2textModel] = textarea.value;
saveImg2textDraftToLocalStorage();       // немедленно
scheduleImg2textDraftServerSync();       // debounce 2000ms → PUT /api/prompt/img2text/rules

// При открытии панели:
// 1. GET /api/prompt/img2text/rules → serverDraft
// 2. localDraft = loadFromLocalStorage()
// 3. Взять свежее по updated_at (или server если localStorage пустой)
```

### Потоки

1. **Открытие панели** → GET rules + GET favorites → render
2. **Смена model tab** → показать `img2textDraft[model]`, фильтровать favorites по новому model
3. **Edit textarea** → дебаунс-sync draft
4. **Load favorite** → если dirty: confirm → set `img2textDraft[model]` + textarea
5. **Save to favorites** → модалка с именем → POST /api/favorites → refresh cache
6. **Convert** → validate+resize image → POST /api/prompt/img2text → show output
7. **Cross-panel Load** → проверить `pendingImg2textLoad` при открытии панели

### Drag-and-drop + resize

```js
// Валидация: MIME ∈ {image/jpeg, image/png, image/webp}, size ≤ 8 MB
// Resize: если long side > 1024px → canvas resize → JPEG q=0.85
// Preview: показать размеры оригинала → «отправлено: WxH, KB»
// Hint под preview: «Resize applied: 1920×1080 → 1024×576»
```

### Image resize — клиентская сторона

```js
async function resizeImageForVision(file) {
    const MAX_SIDE = 1024;
    const QUALITY = 0.85;
    // Если оба размера ≤ MAX_SIDE — конвертировать в JPEG без resize
    // Иначе — scale по long side
    // Вернуть { base64, mime: "image/jpeg", originalW, originalH, sentW, sentH, sentBytes }
}
```

### Inline favorites list

```html
<!-- под textarea, показывать только если img2textFavoritesCache.length > 0 -->
<div class="img2text-favorites-list">
  <span class="list-label">Saved rules (Illustrious)</span>
  <!-- foreach favorite: -->
  <div class="fav-rule-item">
    <span class="fav-rule-name">Detailed tags</span>
    <button onclick="loadImg2textFavorite(id)">Load</button>
    <button onclick="deleteImg2textFavorite(id)">✕</button>
  </div>
  <!-- если сервер вернул ровно 10 записей: -->
  <a class="fav-rule-more" onclick="switchToFavoritesTab()">More in Favorites tab →</a>
</div>
```

### LLM Settings — добавить Vision секцию

```
[ Vision model (for Img2Text) ]
  Input: vision_model (e.g. llava:13b)
  
[ Vision timeout, s ]
  Input: vision_timeout (default: 60)

[ Test Vision ]  → GET /api/llm/vision/health?force=true → показать статус
```

### Глобальная вкладка Favorites

Минимальные изменения:
- Badge **«Img2Text rule»** если `generation_settings?.kind === "img2text_rules"`
- Label поля: «Rule» вместо «Positive prompt»
- Кнопка **«Load in Img2Text»** → `pendingImg2textLoad = { model_id, rule_text }` → переключить на вкладку Prompting

---

## Тесты (`tests/test_img2text.py`)

| Тест | Что проверяет |
|---|---|
| `test_get_draft_empty` | GET без сохранения → дефолтные пустые строки |
| `test_put_draft_roundtrip` | PUT 3 слота → GET → совпадают |
| `test_put_draft_partial_update` | PUT только anima → illustrious/zimage_turbo не затёрты |
| `test_put_draft_invalid_model_key` | PUT с ключом `zit` → 422 |
| `test_post_empty_rule_text` | POST с `rule_text: ""` → 200, `rule_applied: false` |
| `test_post_invalid_model_id` | POST с `model_id: "unknown"` → 422 |
| `test_post_image_too_large` | POST с `len(base64) > 12_000_000` → 413 |
| `test_post_invalid_mime` | POST с `image_mime: "image/gif"` → 400 |
| `test_post_vision_disabled` | `use_llm: false` → 200, `used_llm: false`, `prompt: ""` |
| `test_post_vision_unhealthy` | `vision_model` не отвечает → 400 |
| `test_post_rule_in_user_message` | mock `_chat_vision` → проверить что rule_text в user msg |
| `test_favorites_kind_filter` | GET /api/favorites?kind=img2text_rules → только img2text записи |
| `test_favorites_model_filter` | GET /api/favorites?kind=img2text_rules&model_id=anima → только anima |
| `test_dedupe_illustrious_basic` | `"1girl, long hair, 1girl"` → `"1girl, long hair"` |
| `test_dedupe_illustrious_case` | `"1girl, Long Hair, long hair"` → `"1girl, Long Hair"` |
| `test_dedupe_illustrious_empty` | пустая строка → пустая строка |

---

## Порядок реализации

### Патч A — Backend
1. `LlmSettings`: добавить `vision_model`, `vision_timeout`
2. `LlmHealthReport`: добавить vision-поля
3. `ollama.py`: `_chat_vision()`, `check_vision_health()`
4. Модуль `prompting/prompt_img2text/`: `defaults.py`, `rules.py`, `describe.py`, `normalize.py`
5. API: `GET/PUT /api/prompt/img2text/rules`, `POST /api/prompt/img2text`
6. `GET /api/favorites` расширить query-параметрами `kind` + `model_id`
7. `GET /api/llm/vision/health` (reuse check_vision_health)
8. Тесты

### Патч B — Frontend
1. LLM Settings UI: секция Vision model + Test Vision
2. Новая карточка Img2Text в Prompting tab (HTML + CSS)
3. JS: state, drag-drop, resize, tabs, textarea, draft auto-save
4. JS: inline favorites (load/save/delete)
5. JS: Convert → POST → output + copy
6. Global Favorites: badge + «Load in Img2Text» кнопка + `pendingImg2textLoad`

### Патч C — Интеграция + версия
1. Cross-panel nav (`pendingImg2textLoad` при открытии img2text)
2. CHANGELOG.md
3. Bump версии до `0.2.1` в `pyproject.toml`

---

## Out of scope v0.2.1

- Export JSON (draft + img2text favorites)
- Несколько named profiles одновременно
- Multipart upload
- Server-side image storage
- 3 правила на модель
- Streaming vision response

---

## Зависимости

- Ollama с установленной vision-моделью (llava, bakllava, moondream и др.)
- Нет новых Python-пакетов (используется стандартная `urllib` как в ollama.py)
- Нет изменений схемы БД (favorites таблица без миграции, новый ключ в app_settings)
