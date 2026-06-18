# Прогресс по плану разработки

Чек-лист фаз из `egodary_plan_razrabotki.md`. Обновляется по ходу работы —
это первое, что стоит открыть в начале новой сессии, чтобы понять, где
остановились и что делать дальше.

Подробный список изменений по версиям — в [`CHANGELOG.md`](../CHANGELOG.md).

## Сводка по фазам

| Фаза | Статус | Кратко |
|------|--------|--------|
| 0 | ✅ | Repo, pyproject, README, CHANGELOG, PROGRESS |
| 1 | ✅ | Ядро, `TagRegistry`, `PluginManager`, CLI-каркас |
| 2 | ✅ | Content-packs: camera, lighting, pose, season, style, face, … |
| 3 | ✅ | `PromptState`, `PromptEngine`, сборка buckets → prompt |
| 4 | ✅ | Illustrious + Anima adapters, rules из `rules_pack` |
| 5 | ✅ | Z-Image Turbo (natural language, без negative) |
| 6 | ✅ | Character/outfit/appearance/environment + conflict engines |
| 7 | 🔶 | Fetish pack есть; NSFW rulebook/randomizer — зачатки |
| 8 | 🔶 | Group mode + couple poses; God Mode — 3 пресета; нет Character DNA UI |
| 9 | 🔶 | SQLite (favorites, history, unknown tags, char library); import/converter |
| 10 | 🔶 | Web UI + API в основном готовы; CLI базовый |
| 11 | ⬜ | Forge / ComfyUI — не начато |

Легенда: ✅ готово · 🔶 частично · ⬜ не начато

## Чек-лист (детально)

- [x] **Фаза 0** — Фундамент (repo, pyproject, git, README, CHANGELOG, PROGRESS)
- [x] **Фаза 1** — Ядро домена + загрузчик плагинов (`core/models.py`,
      `core/registry.py`, `core/debug.py`, `plugins/*`, CLI, тесты)
- [x] **Фаза 2** — Content-packs и скрипты сборки каталогов
      (`scripts/build_*_catalog.py`, `update_and_run.bat`):
      `core_tags`, `scene_location_pack`, `camera_pack`, `lighting_pack`,
      `pose_pack`, `face_pack`, `style_pack`, `character_pack`, `outfit_pack`,
      `appearance_pack`, `environment_pack`, `fetish_pack`
- [x] **Фаза 3** — Pipeline (`PromptEngine`, `collect_*_bucket`, `PromptState`,
      conflict preview, quality score)
- [x] **Фаза 4** — Illustrious + Anima: порядок buckets, формат вывода,
      санитайзер Anima; generation rules из `content/rules_pack/models/*.yaml`
      + пользовательские профили в `rules_user/`
- [x] **Фаза 5** — Z-Image Turbo: narrative prompt, `sentence_templates` из YAML
- [x] **Фаза 6** — Тяжёлые паки + `*_rules.yaml`, `cross_rules.yaml`,
      `apply_state_conflicts`, clothing conditions, dress layering
- [ ] **Фаза 7** — Fetish + NSFW Rulebook/Randomizer
      - [x] fetish pack, external skip, subgroup limits
      - [x] `smart_randomize`, `evaluate_rulebook` (минимально)
      - [ ] полноценный NSFW rulebook как в eGen 8.6
      - [ ] осмысленный random по осям clothing/pose/activity/camera
- [ ] **Фаза 8** — Мультиперсонажность, God Mode, Character DNA
      - [x] `group_mode`, couple poses, `CharacterPairState` в модели
      - [x] God Mode bundles (3 пресета в UI)
      - [ ] UI второго персонажа / contrast / DNA
- [ ] **Фаза 9** — Persistence + миграция + import
      - [x] SQLite: favorites, generation_history, unknown_tags, character_presets
      - [x] import prompt → state, converter, runtime registry overlay
      - [x] `migrate_legacy.py` (скрипт)
      - [ ] полный UI для unknown tags / истории генераций
      - [ ] автоматическая миграция legacy JSON при первом запуске
- [ ] **Фаза 10** — Интерфейсы
      - [x] `egodary serve`, FastAPI (`/api/generate`, categories, rules, import, …)
      - [x] веб-UI: все основные вкладки, сессия, Advanced, changelog в UI
      - [x] Quality Boosters (Anima), Restart server, Rules editor
      - [ ] расширение CLI (generate из терминала, batch)
- [ ] **Фаза 11** — Интеграции Forge / ComfyUI (опционально)

## Текущее состояние (июнь 2026)

**Рабочий продукт:** `update_and_run.bat` или `egodary serve` → http://127.0.0.1:8000/

- **13 content-pack** плагинов + `rules_pack` (general + 3 model gen slots)
- **3 модели:** Illustrious, Anima, Z-Image Turbo
- **~100 тестов** (`pytest -q`)
- **Веб-UI:** Style (вкл. Quality Boosters), Character (+ библиотека), Face, Makeup,
  Outfit, Accessories, Pose, Camera, Lighting, Environment, Fetish, Advanced
  (Rules, Import, Session, Server, Debug, Changelog)
- **Конфликты и quality score** в реальном времени в UI
- **Rules:** именованные пользовательские профили (не `user_rule_N`)
- **Score-теги** только для Anima (`quality_boosters.py`)

### Быстрые команды

```bat
update_and_run.bat          rem install + rebuild catalogs + pytest + serve
update_and_run.bat --no-test
restart.bat                 rem kill :8000 + serve
egodary serve
pytest -q
```

## Следующие шаги (приоритет)

1. **Фаза 7** — довести NSFW randomizer / rulebook до уровня eGen 8.6
2. **Фаза 8** — UI второго персонажа и Character DNA (модель `characters` уже есть)
3. **Фаза 9** — UI для unknown tags, просмотр history; миграция legacy «из коробки»
4. **Фаза 10** — `egodary generate` в CLI с тем же pipeline, что и API
5. **Фаза 11** — интеграция с внешним раннером (по необходимости)

Мелкие улучшения по ходу:
- синхронизировать `docs/PROGRESS.md` и `CHANGELOG.md` после каждой сессии с фичами
- `BUILD_NUMBER` / semver при выпуске `0.2.0`

## Договорённости между сессиями

- **Changelog обязателен:** после значимого изменения дополнять [`CHANGELOG.md`](../CHANGELOG.md)
  секцию `[Unreleased]` в той же сессии (в UI видно на Advanced → Changelog).
- **PROGRESS:** обновлять этот файл при смене статуса фазы или приоритетов.
- **Правила моделей:** встроенные — `content/rules_pack/`; пользовательские —
  `rules_user/profiles/` с именами; Illustrious **не** получает score-теги из Quality Boosters.
- **Вёрстка UI:** новые блоки на вкладках — по [`.cursor/rules/web-ui-blocks.mdc`](../.cursor/rules/web-ui-blocks.mdc)
  (отступ 16px между `.card`, Advanced — `.card-grid`).
- **Git:** каждая завершённая фаза/крупная фича — отдельный коммит (когда репозиторий под git).

## Ссылки

| Документ | Назначение |
|----------|------------|
| `CHANGELOG.md` | Что изменилось (для пользователя и агентов) |
| `README.md` | Установка, serve, откат |
| `TRANSFER.md` | Перенос на другую машину |
| `egodary_plan_razrabotki.md` | Исходный план (вне repo, если передан отдельно) |
