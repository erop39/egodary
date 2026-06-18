# Changelog

Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/), версии — semver.
Ведётся с первого коммита: каждая фаза/значимое изменение получает запись здесь
**и** отдельный git-коммит, чтобы можно было откатиться на любую из них
(`git log --oneline`, см. README → «Откат на раннюю версию»).

> **Для агентов и разработчиков:** после значимых изменений (новая фича, API, UI-блок,
> правило генерации) дополняйте секцию `[Unreleased]` в этом файле в той же сессии.
> В UI changelog подгружается с `GET /api/changelog`.

## [Unreleased]

### Changed
- UI v0.1.12: логотип eGOdary в sidebar (`/static/img/logo.png`) и favicon (`/static/img/favicon.png`).
- Tag Studio v0.1.13: модель тегов расширена до совместимого `category + subcategory` (dual-read/dual-write с legacy `subgroup`), добавлены поля `normalized_name`, `aliases`, `is_active`.
- API v0.1.13: `POST /api/categories/{category_id}/items` теперь поддерживает `subcategory_id`, aliases/description/default_weight и встроенную dedupe-проверку.
- Import v0.1.13: classify/merge фиксируют `suggested_subcategory` и `resolution_status` в `unknown_tags`.

### Added
- UI/API v0.1.11: добавлен поток **Add tag** — ввод нового значения тега из интерфейса, выбор `category` и `subgroup`, сохранение в runtime overlay + SQLite, мгновенное появление в chips и участие в генерации.
- Tag Studio v0.1.13: новые endpoint-ы управления тегами (`/api/tag-studio/items`, `/api/tag-studio/deduplicate`, update/move/deactivate runtime items) и endpoint миграции `POST /api/tag-studio/migrate/runtime-subcategory`.
- Tag Studio v0.1.13: добавлен endpoint отката `POST /api/tag-studio/rollback/runtime-subcategory` и rollback checklist `docs/TAG_STUDIO_ROLLBACK.md`.
- Dedupe v0.1.13: выделен `TagDeduplicationService` с exact/alias/fuzzy проверками для ручного добавления и import merge.
- UI v0.1.13: Add tag modal расширен полями Subcategory, Aliases, Description, Default weight.
- Style v0.1.10: подгруппа **NSFW** (uncensored, nude, explicit, spicy) в Aesthetic / Mood; лимиты multi-select — Quality до 8, Aesthetic до 56, Technique до 6.
- UI v0.1.8: Prompting — кнопки Copy и ⭐ (избранное) у результатов Prompt Analyze и NSFW Styler.
- Prompt Analyze: ZIT convert v1.1 — rule-based narrative (без meta-тегов, 1girl/solo → natural opener, 8 секций, lighting до camera) + опциональный LLM refine.
- Prompt Analyze: единый convert-пайплайн text/JSON → JSON v1.2 → Illustrious / Anima / Z-Image (по grok_report).
- Prompt Analyze: Target **JSON** — конвертация промпта в структурированный JSON (schema v1.2) по правилам production-ready prompting.
- Favorites v0.1.1: отдельная вкладка Favorites (sidebar), просмотр сохранённого промпта, редактирование, preview-ссылка и переход к генерации, seed в generation settings, иконка добавления в избранное из блока Positive.
- v0.1.2: загрузка избранного промпта в Prompt Analyze (иконки ✎ в списке, превью и на панели Analyze).
- v0.1.2: отдельная вкладка **LLM Settings** в нижней части sidebar.
- UI v0.1.7: прогресс-бар при LLM-операциях (NSFW refine, classify, convert, health check) с таймером и оценкой по Timeout.
- NSFW Styler v0.1.8: LLM видит исходный промпт и unknown phrases; режим **LLM full rewrite**; extreme усилен (реальные теги каталога); подсказка в UI.
- NSFW Styler v0.1.9: **User prompt rewrite** — своя инструкция для LLM (приоритет над правилами eGOdary), прямой rewrite без каталога.
- NSFW Styler v0.1.10: «Сохранить идентичность» фиксирует только лицо/волосы/пропорции тела; одежда, поза, выражение и сцена доступны для NSFW.

### Fixed
- Startup performance v0.1.14: перенесена тяжёлая cold-start инициализация engine на backend startup, чтобы первый запрос `outfit.clothing_condition` не блокировал UI на старте.
- LLM Settings: подключение к локальному Ollama на Windows при включённом системном прокси (обход proxy для localhost/127.0.0.1).
- LLM Settings: JSON probe не обрывался по таймауту 15 с при холодном старте модели (используется Timeout из настроек).
- LLM Settings: модель `llama3` распознаётся при установленном теге `llama3:latest`.
- Runtime persistence v0.1.13: миграционный backfill для overlay-записей (`subgroup -> subcategory_id`) и нормализация метаданных без изменения схемы `runtime_tag_items`.

### Changed
- Runtime tag API v0.1.11: новый endpoint `POST /api/categories/{category_id}/items` с нормализацией `item_id`, валидацией subgroup и автозаполнением model-variants тегов.
- UI v0.1.1: Buckets debug перенесён в Advanced → Debug, блок God Mode удалён из Advanced и фронтенд-логики.
- Results v0.1.1: у model chips убраны кнопки Off/Random, кнопки сохранения/загрузки JSON перенесены в правый sidebar рядом с Generate/Random (иконки).
- v0.1.2: **Advanced** и **Restart server** перенесены вниз левого sidebar; Restart — в footer над версией.
- v0.1.2: **Сброс** сессии — иконка ↺ в правом sidebar рядом с Save/Load.
- v0.1.2: LLM Settings вынесены из Advanced в отдельную категорию над Advanced.
- v0.1.2: правило версионирования — `.cursor/rules/versioning.mdc` (+0.0.1 и CHANGELOG при фичах / глобальных настройках / >2 правок).

### Добавлено

#### Контент-паки и каталоги
- **Character pack** — тело, пропорции, детали; вкладка Character + библиотека пресетов.
- **Face pack** — 11 категорий, ~290+ тегов; вкладка Face.
- **Pose pack** — Solo (90) + Couple (64); couple с Group mode.
- **Clothing conditions** — wear/damage/wet dropdown под outfit (131 condition).
- **Outfit pack** — dress/top/bottom/underwear/legwear/jacket/footwear/gloves/cape с подкатегориями и layering rules.
- **Appearance pack** — hair, hair color, makeup, accessories.
- **Style pack** — art style, artist, quality, aesthetic, technique; дерево подкатегорий, multi-select лимиты.
- **Camera pack** — angle, framing, lens, focus, composition, nsfw shot; пресеты в UI.
- **Lighting pack** — light type, direction, quality, color mood, nsfw; пресеты.
- **Environment pack** — location, situation, modifiers; cross-rules с scene/weather.
- **Fetish pack** — elements по подгруппам, external skip, conflicts.
- **Scene / location** — `scene.time`, `weather`, `season`, `scene.location`.
- **Скрипты сборки** — `scripts/build_*_catalog.py`, `update_and_run.bat` (pip install → rebuild catalogs → pytest → serve), `restart.bat`.

#### Pipeline и модели
- **PromptEngine** — сборка `PromptBuckets` → адаптер модели → positive/negative.
- **Illustrious** — danbooru tag order, dedupe, technical suffix; правила из `rules_pack/models/illustrious.yaml`.
- **Anima** — 14-блочный формат, санитайзер photo/bokeh, strip boilerplate; правила из `rules_pack/models/anima.yaml`.
- **Z-Image Turbo** — natural language, sentence templates из `rules_pack/models/zimage_turbo.yaml`.
- **Conflict engine** — pack-local rules + `cross_rules.yaml`; preview в UI (оранжевые warnings).
- **Quality score** — оценка 0–100, penalties/bonuses из general rules; панель в правой колонке.
- **Import / convert** — разбор промпта в `PromptState`, unknown tags в SQLite.
- **Runtime registry** — overlay тегов при импорте (`/api/prompt/import/*`).
- **NSFW styler** — `POST /api/prompt/nsfw-style`.
- **God Mode bundles** — пресеты на вкладке Advanced.
- **Quality Boosters** (Style) — уровни Low/Medium/High для score-тегов; **только Anima**.

#### Rules (Advanced)
- Слоты: **General**, **Illustrious Gen**, **Anima Gen**, **ZIT Gen**.
- Встроенные правила (`content/rules_pack/`) + пользовательские именованные профили (`rules_user/profiles/`).
- UI: Load file → имя → Save, выбор профиля, редактор YAML, Delete, Use default.
- API: `GET/POST /api/rules/*`, сброс active profile.

#### Web UI
- Полный интерфейс: вкладки Style, Character, Face, Makeup, Outfit, Accessories, Pose, Camera, Lighting, Environment, Fetish, Advanced.
- Деревья категорий, chips Off/Random, счётчики выбора на nav и в дереве.
- Сессия: автосохранение в `localStorage`, экспорт/импорт JSON.
- Import prompt → state на Advanced.
- **Restart server** — карточка Server на Advanced, `POST /api/server/restart` (перезапуск uvicorn worker).
- Русские tooltips тегов (`tag-tooltips-ru.js`, ~3300 записей).
- Правило вёрстки новых блоков: `.cursor/rules/web-ui-blocks.mdc`.

#### API (основное)
- `POST /api/generate`, `/preview`, `/random`
- `POST /api/conflicts/preview`, `/api/quality/preview`
- `POST /api/import`, `/api/convert`
- `GET/POST /api/character-library`, `/api/favorites`, `/api/unknown-tags`
- `GET /api/categories`, `GET /api/changelog`, `GET /api/debug`
- `POST /api/server/restart`

#### Тесты
- **100+ тестов**: pipeline, adapters, rules loader, style/character packs, quality score, environment cross-rules, import, runtime registry, server restart, plugin loader, content migration.

### Изменено
- **Rules profiles** — вместо авто `user_rule_1…N` только именованные профили с `profiles_meta.yaml`.
- **Anima / ZIT adapters** — читают generation rules из YAML (раньше часть была захардкожена в Python).
- **Quality Boosters** — score-теги (`score_9`, `score_8_up`, `score_7_up`) не добавляются для **Illustrious** и ZIT.
- Отступы между карточками на вкладках: `.panel > .card + .card { margin-top: 16px }`.
- Возраст персонажа: slider 14–60, default 18.
- Dress layering: micro/sheer/bodysuit платья допускают top + underwear_layer + legwear.
- Chip Off / Random — исправлено сохранение active state.

### Исправлено
- **Illustrious + score-теги:** явная фильтрация `score_*` из quality bucket (не только отключение boosters); `serve --reload` теперь следит за `egodary/core/`, `api/`, `models_adapters/`.
- Накопление мусорных `user_rule_*.yaml` на вкладке General Rules.
- Слипание блоков Style / Quality Boosters из-за отсутствия margin между соседними `.card`.

---

## [0.1.0] — 2025 — ранний UI-каркас (частично включено в Unreleased выше)

### Добавлено
- Структура репозитория (`pyproject.toml`, src-layout `egodary/`, `tests/`, `docs/`, `plugins_user/`).
- `egodary.core.models` — базовые Pydantic-модели: `TagItem`, `TagCategory`, `ConflictGroup`.
- `egodary.core.registry.TagRegistry` — реестр категорий тегов с защитой от дублей id
  (категории и теги внутри категории) и счётчиком источников (какой плагин что зарегистрировал).
- `egodary.core.debug` — функция `get_debug_snapshot()`: версия, список загруженных
  плагинов, сводка по реестру. Это прямой аналог вкладки **Debug** из eGen 8.6,
  адаптированный под архитектуру с плагинами.
- `egodary.plugins.manifest` — Pydantic-схема `manifest.toml` (`PluginManifest`) +
  парсинг через `tomllib`.
- `egodary.plugins.base` — протоколы `ContentPackPlugin`, `PipelineStagePlugin`,
  `IntegrationPlugin` (заготовка; `ModelAdapterPlugin` будет в фазе 4–5).
- `egodary.plugins.loader.PluginManager` — обнаружение плагинов из трёх источников:
  встроенные паки (`egodary/content/*/manifest.toml`), пользовательские drop-in
  (`plugins_user/*/manifest.toml`), установленные через `entry_points` группы
  `egodary.plugins`. Дублирующиеся id плагинов/тегов — явная ошибка при загрузке,
  а не молчаливая перезапись.
- Первый реальный content-pack: `egodary/content/core_time_weather` (категории
  `scene.time_of_day` и `scene.weather` — перенос `TIME_TAGS`/`WEATHER_TAGS` из
  eGen 8.6, нейтральные данные, без зависимостей). Используется как живой пример
  формата `manifest.toml` + `tags.yaml` для всех будущих контент-паков.
- CLI на Typer: `egodary version`, `egodary plugins list`, `egodary registry show <category>`,
  `egodary debug`, `egodary serve`.
- Тесты: загрузка манифеста, обнаружение дублей id в реестре, сквозной прогон
  загрузки `core_time_weather` через `PluginManager`.
- `docs/PROGRESS.md` — чек-лист фаз 0–11 из плана разработки, обновляется по ходу работы.

### Решения / допущения этой фазы
- Правила вывода под конкретные модели (Illustrious/Anima/Z-Image Turbo) **не переносятся
  и не меняются на этом шаге** — по договорённости, они остаются как в исходнике до
  отдельной фазы 4–5 и будут донастраиваться позже.
- Состояние генерации (`PromptState`) пока не вводится — оно появится в фазе 3 вместе
  с pipeline, чтобы не создавать модель "заранее и наугад".
