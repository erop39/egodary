# Changelog

Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/), версии — semver.
Ведётся с первого коммита: каждая фаза/значимое изменение получает запись здесь
**и** отдельный git-коммит, чтобы можно было откатиться на любую из них
(`git log --oneline`, см. README → «Откат на раннюю версию»).

> **Для агентов и разработчиков:** после значимых изменений (новая фича, API, UI-блок,
> правило генерации) дополняйте секцию `[Unreleased]` в этом файле в той же сессии.
> В UI changelog подгружается с `GET /api/changelog`.

## [Unreleased]

### Added
- **Forge / A1111 интеграция** — прямая отправка в локально запущенный Forge (или vanilla A1111)
  из UI без копирования промпта.
  - Карточка **Send to Forge ▶** появляется автоматически, когда Forge включён в Advanced → Forge;
    содержит статус-точку, hint с URL/steps/CFG, inline-слайдер batch (1–4) и прогресс-бар.
  - **Batch size 1–4:** генерируются N изображений за один вызов; при batch > 1 показывается
    кликабельная сетка-миниатюр, выбор тайла обновляет главное изображение и seed для hires.
    Кнопки «⬇ Save» (одно) и «⬇ Save all» (ZIP через JSZip CDN).
  - **Прогресс-бар:** поллинг `/sdapi/v1/progress` каждые 600 мс; фаза txt2img vs hires по
    `job_no`/`job_count`; shimmer-скелет вместо сломанной иконки во время ожидания.
  - **Generation settings** под выходным изображением: сетка ключ/значение с реальными параметрами
    отправленного запроса (steps, CFG, sampler, seed, размер и т.д.).
  - **Hires fix:** scale, upscaler, steps, denoising, hires CFG, resize W/H — все поля в сайдбаре
    и в Quick Settings.
  - **Quick Settings:** автосохранение перед отправкой (чтобы UI-значения применялись, а не
    старые из DB); поля sampler, scheduler, batch size, hires CFG, hires resize W/H.
  - **↺ Reload** — перезагружает все списки из Forge API; тост показывает счётчики по категориям.
  - API: `GET /api/forge/catalog` — один запрос возвращает models + samplers + upscalers +
    schedulers + counts (вместо четырёх отдельных); роуты `/api/forge/progress`,
    `/api/forge/send`, `/api/forge/health`, `/api/forge/settings`.
  - Настройки: `catalog_timeout` (30 с, для медленного сканирования моделей) отдельно от
    `timeout` (10 с, для обычных запросов); `batch_size`, `hires_cfg`, `hires_resize_x/y`
    добавлены в `FORGE_DEFAULTS`.

### Fixed
- **Hires качество деградировало vs Forge-UI** при идентичных настройках — два бага:
  (1) `hr_additional_modules: ["Use same choices"]` мешал применению LoRA-весов в API-режиме —
  поле полностью удалено из payload; (2) проверка `if not payload.get("denoising_strength")`
  ошибочно перезаписывала значение `0.0` (корректный «без изменений») — исправлено на
  `if "denoising_strength" not in payload`.
- **Все списки Forge (модели, samplers, upscalers, schedulers) теперь отсортированы
  по алфавиту** (`key=str.lower`), дедuplicated через set; упал один тайм-аут — использован
  `catalog_timeout=30 s` вместо `timeout=10 s` для медленных catalog-эндпоинтов.
- **`_SCHEDULER_FALLBACK`** расширен: добавлены `Automatic`, `Beta`, `LCM`, `Turbo`,
  `Linear Quadratic`, `Polyexponential` — полный список, который Forge возвращает по API.
- **Batch size = 4 генерировал только 1 изображение** — кнопка Send читала значение из DB,
  а не из UI. Фикс: `btn-forge-send` теперь вызывает `applyForgeQuickSettings()` перед
  отправкой, чтобы все UI-значения попали в DB.
- Скелет-placeholder убран из потока документа в idle-состоянии (добавлен `hidden` по умолчанию);
  устранён пустой блок между кнопкой Send и прогресс-баром.
- Batch-значение (`4`) больше не выходит за границы карточки — `min-width:0` на flex-контейнере.

### Changed
- **Batch size** вынесен из Advanced-сайдбара в inline range-slider рядом с кнопкой
  «Send to Forge ▶» (значение обновляется live при перетаскивании, синхронизируется из
  сохранённых настроек).
- `loadForgeOptions()` переключён на `/api/forge/catalog` (один round-trip вместо четырёх);
  при ручном **↺ Reload** показывает тост `«Forge loaded: N models · M samplers · …»`.
- Все `fetch_forge_*` функции используют `except Exception` + `logger.warning` — любая ошибка
  API логируется и не ломает остальные списки.

### Tests
- **Параллельный запуск тестов** через `pytest-xdist`: `addopts = "-n auto"` в `pyproject.toml`,
  `pytest-xdist>=3.0` добавлен в `[dev]`-зависимости. Время прогона: **15 с → ~10 с**.
- `test_forge_send_enabled_but_unreachable`: `gen_timeout=0.05` — TCP-попытка завершается
  за <300 мс вместо ожидания полного 10-секундного таймаута (экономит ~2 с).
- `tests/conftest.py`: session-scoped фикстура `loaded_plugin_manager` кэширует
  `PluginManager.load_all()` один раз на сессию; `test_loader_loads_ui_extension` переключён
  на неё.
- 284 passed (все тесты зелёные).

### Fixed
- **`update_and_run.bat` закрывалось с "[ERROR] Server failed to start." после обычной остановки
  сервера Ctrl+C.** Сервер на Windows часто возвращает ненулевой код выхода именно при штатной
  остановке через Ctrl+C — скрипт принимал это за реальный сбой запуска, показывал [ERROR] и уходил
  в `:fail` (`pause` → закрытие окна по нажатию клавиши). Теперь после остановки сервера (по любой
  причине — Ctrl+C или реальный сбой) пишется нейтральное "Server stopped." без алармистского
  [ERROR]; если сервер правда не запустился, причина и так видна в выводе uvicorn выше. Тот же фикс
  внесён в `restart.bat` (там был идентичный паттерн).
- **В подсказке "To skip tests: ... (or --fast ...)" (добавленной в прошлом патче) ломался парсинг
  cmd.exe.** Строка лежит внутри уже открытого блока `if errorlevel 1 ( ... )` — непроэкранированные
  `(`/`)` внутри активного блока cmd.exe воспринимает как часть блочной структуры, а не как текст:
  вторая половина подсказки уходила в отдельную "не опознанную команду". Скобки в этой строке
  экранированы (`^(`/`^)`).
  Оба бага найдены не статическим чтением, а реальным прогоном скрипта: поставил `wine` +
  `gcc-mingw-w64` в песочнице, собрал нативный exe-заглушку для `python`, прогнал
  `update_and_run.bat`/`restart.bat` под `wine cmd` с разными кодами возврата заглушки (успех/pip
  упал/один build-скрипт упал/тесты упали/serve "упал") — так подтверждены и сами баги, и оба фикса
  для всех шести сценариев.
- **Ветка дерева для wildcard-подгруппы подписывалась именем файла, а не тем, что введено в
  Subgroup.** Например: Category = `appearance.hair`, Subgroup = "Sexy outfit", файл
  `random_filename_v3.txt` — лист в дереве показывал `🧩 random_filename_v3.txt` вместо
  `🧩 Sexy Outfit`. `injectWildcardLeaves()` брал `label` загруженного файла (есть только при
  нескольких файлах в одной подгруппе он ещё и произвольно "побеждает" — какой файл попался первым
  при переборе). Теперь подпись листа строится из самого названия подгруппы (humanize:
  `sexy_outfit` → `Sexy Outfit`, уже нормально набранное "Sexy outfit" остаётся как есть) — это и
  есть то, что пользователь явно ввёл как имя группы. Имя файла по-прежнему видно в списке вкладки
  Wildcards и в инлайн-секции "🧩 Wildcards" под *другими* подгруппами, где различать файлы
  действительно нужно.

- **В промпт попадала локация, которую пользователь не выбирал.** Сборка "scene"-бакета в
  `core/pipeline.py` добавляла значения `scene.location` (старая плоская категория, без какого-
  либо UI-контрола в текущем приложении — заменена деревом Environment → Location) И
  `environment.location` (актуальное дерево Indoor / Outdoor & Semi-Outdoor / Fantasy & Stylized)
  **одновременно**, если оба поля state были непустыми — вместо того чтобы трактовать их как
  альтернативы, как это уже корректно делают `core/conflicts.py` и `core/rule_matching.py`
  (`env.location or state.scene.location`). Если в сессии оставалось старое значение
  `scene.location` (например `luxury_apartment` — оно могло попасть туда давно, ещё через
  отсутствующий ныне UI или из старого сохранённого `.json`), в промпт всегда добавлялся текст
  ЭТОЙ локации в довесок к тому, что реально выбрано в дереве Indoor/Outdoor/Fantasy — даже
  если визуально в UI был подсвечен только один, совсем другой чип.
  Подтверждено 1:1 по скриншоту пользователя: `anima`-тег айтема `luxury_apartment` из
  `scene_location_pack/location.yaml` — `"luxury apartment with floor-to-ceiling windows and city
  view"` — дословно совпадал с "лишним" куском промпта.
  Фикс: `_collect_scene_bucket` теперь использует `env.location or scene.location` — берёт ровно
  ОДНО значение (приоритет у актуального `environment.location`), `scene.location` остаётся
  рабочим fallback'ом только для старых сессий, где `environment.location` вообще не задан.
  Тест: `test_scene_location_and_environment_location_are_alternatives_not_both`.

### Added
- **Перенос тега прямо из окна "Edit tag".** Раньше перенести тег в другую category/subcategory
  можно было только отдельной формой "Move tag" внизу панели Tag Studio — теперь поля Category и
  Subcategory есть и в самой модалке Edit, рядом с остальными полями: меняешь их и жмёшь Save,
  тег переезжает вместе с обновлением label/aliases/тегов моделей за одно действие.
  - Subcategory-поле — свободный текстовый ввод с datalist (как Move tag/Wildcards/Add tag).
  - Смена category работает только для runtime-тегов — то же ограничение, что и у отдельной кнопки
    Move tag (core-тег нельзя "телепортировать" между категориями; сначала любое сохранение в Edit
    форкает его в runtime-копию, дальше его уже можно переносить полноценно). Для core-тега поле
    Category в модалке заблокировано (с подсказкой), доступна только смена подгруппы внутри той
    же категории — это уже работало раньше неявно через `PUT .../items/{id}` (форк + subcategory),
    просто не было видно в UI.
  - Технически: смена подгруппы внутри той же категории идёт одним `PUT` (эндпоинт уже это умел —
    `subcategory_id` + `allow_new_subcategory`). Смена самой категории — `PUT` (без subcategory)
    сразу следом `POST .../move` с `to_category_id` и `to_subcategory_id` за один клик Save,
    отдельного шага не требуется.
  - Проверено: Node-харнесс с подменой `api()` — 3 сценария (смена только подгруппы у runtime-тега,
    смена категории у runtime-тега, смена подгруппы у core-тега) дают ожидаемую последовательность
    запросов и тел. Сквозной curl-тест: тег создан в `outfit.dress/micro_mini`, после
    PUT+move лежит в `outfit.top/brand_new_via_edit_modal`.

### Fixed
- **Модалка «+ Add tag» — тот же баг, что и в Move tag/Wildcards, последний оставшийся случай.**
  После фикса Move tag сделал полный аудит: прогрепал все `<select>` в `index.html`, все места в
  `app.js`, пишущие `subcategory_id`/`subgroup`, и все вызовы `POST .../items`. Нашёл ровно ОДИН
  оставшийся случай — поле Subcategory в модалке "+ Add tag" (`add-tag-subgroup`): закрытый
  `<select>`, заполнялся только уже существующими подгруппами, плюс сам fetch не отправлял
  `allow_new_subcategory: true`, так что даже при ручном вводе бэкенд ответил бы 400. Подтвердил
  curl'ом: тот же payload без флага — 400 "Invalid subcategory…", с флагом — 200.
  Поле сконвертировано в свободный текстовый ввод с datalist-подсказками (как Move tag и
  Wildcards); `createTagFromModal()` теперь всегда шлёт `allow_new_subcategory: true`; префилл
  подгруппы при открытии модалки по кнопке "+" внутри панели подгруппы больше не требует, чтобы
  значение уже было «известным».
  Остальные `<select>` в Tag Studio (Lister-фильтр, пикеры category) — это либо фильтры поиска
  (где закрытый список корректен: фильтровать по несуществующей подгруппе бессмысленно), либо
  выбор category (фиксированный набор, не подгруппа) — их трогать было не нужно.

- **Move tag в Tag Studio не работал при переносе в некоторые подгруппы.** Та же
  закрытая-`<select>`-проблема, что и в форме Wildcards / модалке "+ Add tag": поле "Move to
  subcategory" заполнялось только подгруппами, в которых **уже есть хотя бы один тег**
  (`GET /api/categories/{id}` → `subcategories` строится из фактических тегов категории). Если
  целевая подгруппа была пустой (включая абсолютно новую, ещё не существующую) — её просто не
  было среди опций `<select>`, перенести тег туда было физически нечем выбрать. Бэкенд
  (`POST /.../items/{id}/move`) при этом уже полностью поддерживал перенос в любую новую
  подкатегорию без ограничений — проверил руками через curl до правки. Поле сделано свободным
  текстовым вводом с datalist-подсказками существующих подгрупп (как и в Wildcards) — можно
  выбрать из списка или вписать новое имя. Добавлен регрессионный тест
  (`test_api_move_runtime_tag_item_into_brand_new_subcategory`) — для этого эндпоинта раньше не
  было тестового покрытия вообще.

### Added
- **Condition «Unzipped to waist»** в группе Partial Removal & Exposure (`outfit.clothing_state`,
  `partial_removal`), рядом с Open / Unbuttoned и Slid off shoulders.

### Fixed
- **Цветовые condition-теги для одежды («мы добавляли, их нет»).** Данные были полностью на
  месте: 26 тегов с `dimension: color` / `group: Color` в `outfit/tags/clothing_state.yaml`,
  бэкенд их честно отдавал (`GET /api/categories/outfit.clothing_state`), и сборка промпта
  (`core/clothing_state_bind.py::CLOTHING_STATE_DIMENSION_ORDER`) уже знала про `color`. Не
  хватало только UI: список измерений для аккордеона условий одежды (`CLOTHING_STATE_DIMENSIONS`
  в `app.js`) — отдельный, захардкоженный массив — никогда не обновлялся после добавления цвета,
  поэтому секция "Color" просто не рендерилась, хотя теги были полностью рабочими (их можно было
  выставить только в обход UI, например через JSON-импорт сессии). Добавлена недостающая запись
  `{ id: "color", label: "Color" }` в порядке, соответствующем YAML (между Stains & Fluids и
  Additional states).
- **Тег из одного wildcard-файла «исчезал», если строка с тем же текстом встречалась в другом
  файле.** `item_id` каждой строки генерируется детерминированно из текста (slugify) и до сих пор
  деduplicate-ился только *внутри* одного файла (`make_item_id` / `used_ids` — см.
  `egodary/core/wildcards.py`). Когда два РАЗНЫХ загруженных файла содержали строку с одинаковым
  текстом (вполне реальный кейс для похожих по теме списков — причёски, позы и т.п.), оба тега
  попадали в `RuntimeRegistry` с одинаковым id, и `add_item(..., on_conflict="skip")` молча
  отбрасывал тег из второго (по порядку обработки) файла — без какой-либо ошибки или
  предупреждения в UI. Поскольку порядок чтения файлов из SQLite не гарантирован (`SELECT`
  без `ORDER BY`), какой именно файл «терял» тег могло меняться от запуска к запуску — отсюда
  ощущение, что «при загрузке нового файла происходит перезапись и старый исчезает».
  Воспроизвёл и подтвердил руками (curl): два файла с единственной строкой `Long bangs` каждый —
  до фикса в каталоге `appearance.hair` оставался только один экземпляр тега вместо двух.
  Теперь id тега в реестре всегда содержит префикс `wc{wildcard_id}_...` — коллизия между
  РАЗНЫМИ файлами невозможна в принципе, тег пропадает только когда удалён сам файл (или его
  собственная строка выключена чекбоксом) во вкладке Wildcards, как и требовалось.
  - `egodary/persistence/schema.py::load_wildcards_into_registry` — namespaced id при merge в
    реестр; собственный `item_id` в таблице `wildcard_items` (используется для чекбокса
    включения отдельной строки) не менялся.
  - `GET /api/wildcards/by-category/{category_id}` — отдаёт тот же namespaced id, которым
    реально оперирует реестр, чтобы выбор тега из дерева/секции Wildcards совпадал с тем, что
    действительно попадёт в промпт.
  - Новый регрессионный тест: `test_load_wildcards_into_registry_two_files_same_text_dont_collide`.
    Обновлены 3 существующих теста, жёстко зависевших от старого (без namespace) формата id.

### Added
- **Отдельная ветка дерева для новых wildcard-подгрупп.** Раньше wildcard с произвольным
  `target_subgroup` (например `appearance.hair` / `imported`) был виден только как
  дополнительный блок «🧩 Wildcards», приклеенный снизу к *каждой* существующей подгруппе
  категории (Long Styles, Updos & Buns и т.д.) — без своего отдельного узла в дереве слева.
  Теперь `injectWildcardLeaves()` (по той же схеме, что уже использует `injectPresetsIntoTree`
  для пресетов) добавляет для такой подгруппы собственный лист дерева — `🧩 hair test.txt` —
  рядом с остальными ветками Hair, со своими чипами, выбираемыми точно так же, как у обычных
  подгрупп. `field`/`multi`/`conditionField` нового листа копируются с соседнего листа той же
  categoryId, поэтому он читает/пишет то же поле state, что и его «настоящие» соседи. Работает
  для произвольной глубины вложенности (например `Accessories → Tattoos & Body Art`) и для
  групп, смешивающих несколько categoryId под одним заголовком (например `Hair` = `appearance.hair`
  + `appearance.hair_color`, `Bottom` = `outfit.bottom` + `outfit.underwear_layer`).
  Индекс (`GET /api/wildcards`, без построчных items — достаточно для построения дерева)
  грузится один раз при старте приложения, до первого рендера дерева, и пересчитывается после
  любого upload/toggle/delete во вкладке Wildcards.
  Блок «🧩 Wildcards» внутри обычных подгрупп больше не дублирует подгруппу, которая теперь
  доступна как отдельный лист (фильтруется по `target_subgroup !== текущая subgroup`).

### Fixed
- **Wildcards-секция внутри подгрупп.** Каждая панель подгруппы (Outfit, Character/Hair,
  Makeup, Accessories, Pose, Camera, Lighting, Environment, Fetish и т.д.) теперь показывает
  блок «🧩 Wildcards» со всеми тегами, загруженными через вкладку Wildcards для родительской
  категории этой подгруппы — независимо от того, совпадает ли `target_subgroup`, заданный при
  загрузке, со встроенным id подгруппы в дереве. Раньше теги, загруженные с произвольным/новым
  именем подгруппы (например `test`), не появлялись вообще нигде в интерфейсе — они уже лежали
  в `RuntimeRegistry` и участвовали в генерации, но физически не на чем было их увидеть, т.к.
  фильтрация чипов по подгруппе (`filterItemsBySubgroup`) требует точного совпадения id.
  Секция читает `GET /api/wildcards/by-category/{category_id}` (новый эндпоинт) и автоматически
  пропадает, если у категории нет включённых wildcard-файлов — либо если конкретный файл/строка
  выключены чекбоксом во вкладке Wildcards (что и было главным требованием: «при выключении —
  раздел не отображается»).
  - Бэкенд: `GET /api/wildcards/by-category/{category_id}` — отдаёт только enabled wildcards
    с их enabled строками, сгруппированными по исходному файлу.
  - Фронтенд: `appendWildcardsSection()` дергается из `loadCategoryChips()` /
    `loadCategoryMultiChips()` после рендера обычных чипов, с простым кэшем по categoryId
    (инвалидируется при upload/toggle/delete wildcard) и защитой от гонки при быстром
    переключении подгрупп (`dataset.wcToken`).
- **Plugins-карточка во вкладке Advanced.** Бэкенд (`GET /api/plugins`,
  `POST /api/plugins/{id}/enable|disable`) существовал, но не имел ни одного потребителя во
  фронтенде — раздел управления плагинами из UI отсутствовал полностью (ни одного упоминания
  `plugin` в `app.js`/`index.html`). Добавлена карточка со списком drop-in плагинов
  (`plugins_user/`), чекбоксом enable/disable на каждый и подсказкой про необходимость
  перезапуска сервера после переключения.

### Fixed
- **`ui_extension.register()` падал на каждом старте сервера.** Плагин `advanced_prompting`
  вызывает `app.add_middleware(...)` в своём `register()`, а `register_ui_extensions(app)`
  вызывался изнутри `lifespan`-хендлера — но Starlette фиксирует middleware-стек на самом первом
  ASGI-вызове приложения, включая сам `lifespan`-scope, то есть `add_middleware()` гарантированно
  бросает `RuntimeError: Cannot add middleware after an application has started` ещё до того, как
  выполнится код плагина. Ошибка перехватывалась в `PluginManager.register_ui_extensions()` и
  молча логировалась — поэтому `advanced_prompting` фактически никогда не регистрировал свою
  UI-инъекцию ни на одном запуске. Регистрация перенесена на уровень модуля — сразу после
  создания `FastAPI(...)`, до первого ASGI-вызова.
- Удалена осиротевшая дублирующая папка `plugins_user/advanced_prompting.disabled` (байт-в-байт
  совпадала с активной `advanced_prompting/`, не считая `__pycache__`) — из-за неё
  `GET /api/plugins` отдавал один и тот же плагин дважды: включённым и выключенным одновременно.
- Поле Subgroup на вкладке Wildcards: `<datalist id="wildcards-subgroup-options">` существовал
  в разметке, но никогда не заполнялся — отсюда и опечатки/случайные новые подгруппы при загрузке
  (см. пункт выше). Теперь при выборе категории подсказки подтягиваются из
  `subcategories` соответствующего `GET /api/categories/{id}`.
- **`GET /` падал на каждый запрос после того, как заработала регистрация `ui_extension`
  (предыдущий пункт).** `InjectScriptMiddleware` плагина `advanced_prompting`
  (`plugins_user/advanced_prompting/advanced_prompting/plugin.py`) дописывает `<script>` в тело
  `index.html`, но собирала заголовки нового `Response` через `dict(response.headers)` —
  включая уже устаревший `content-length` от оригинального (более короткого) тела. Starlette не
  пересчитывает `content-length`, если он уже присутствует в переданных headers, поэтому uvicorn
  обнаруживал расхождение между реальным телом и заявленной длиной и ронял запрос:
  `RuntimeError: Response content longer than Content-Length`. Эта ветка кода была годами мертва
  из-за предыдущего бага (middleware вообще не регистрировался) — поэтому и не проявлялась раньше.
  Теперь `content-length`/`content-encoding` выкидываются из скопированных headers перед
  созданием нового `Response`, чтобы Starlette посчитал их заново.

### Debug
- Проверено: `pytest tests/` — 251 passed, без регрессий от переноса регистрации плагинов.
- Проверено вручную (curl, поднятый локально `uvicorn`): чистый старт без ошибок в логе,
  `/api/plugins` отдаёт один корректный объект, enable/disable round-trip переименовывает папку
  туда-обратно, `/api/wildcards/by-category/appearance.hair` отдаёт ранее «потерянные» 15 тегов
  из `hair test.txt` (target_subgroup=`test`).
- Проверено вручную: `GET /` после фикса возвращает `200 OK`, `content-length` в заголовке точно
  совпадает с фактическим размером тела ответа, инжектированный `<script>` присутствует перед
  `</body>`, в логе сервера — чистый `200 OK` без traceback.
- `injectWildcardLeaves()` прогнан изолированным Node-харнессом (без браузера) против реальных
  `HAIR_TREE`/`OUTFIT_TREE`/`ACCESSORIES_TREE`/полного `getCharacterTree()`: лист корректно
  добавляется на верхнем уровне (Hair), внутри вложенной на 2 уровня группы (Accessories →
  Tattoos & Body Art), в группе с несколькими categoryId (Bottom = outfit.bottom +
  outfit.underwear_layer), и не добавляется при пустом индексе wildcards.
- `pytest tests/` — 252 passed (251 + новый регрессионный тест на коллизию id между файлами).
  Проверено вручную (curl): два файла с совпадающей строкой `Long bangs` — до фикса жил только
  один экземпляр тега в `appearance.hair`, после фикса оба, с разными `wc{id}_long_bangs`.
- `pytest tests/` — 252 passed. Проверено вручную (curl `/api/generate`): condition
  `partial_removal: unzipped_to_waist` + `color: red` на `black_harness_top` →
  `"unzipped to waist red black harness top"` в positive prompt.
- `pytest tests/` — 253 passed. Проверено вручную (curl): `POST /.../move` с
  `to_subcategory_id` на несуществующую подгруппу `brand_new_subgroup_xyz` — 200 OK, тег
  корректно переехал.
- `pytest tests/` — 253 passed (без новых тестов: backend-валидация `allow_new_subcategory` уже
  была покрыта тестом `test_api_add_runtime_tag_item_supports_new_subcategory_when_enabled`).
  Проверено вручную (curl), тот же payload, что теперь шлёт модалка: без `allow_new_subcategory`
  → 400 "Invalid subcategory…", с флагом → 200, тег создан с нужной подгруппой.

## [0.1.35] — 2026-06-20

### Added
- **Wildcards** — новый раздел в левом меню для загрузки собственных текстовых списков тегов.
  Пользователь загружает `.txt` файл (одна фраза на строку, маркеры `*`/`-`/`•` опциональны),
  выбирает существующую категорию генератора и подгруппу (существующую или новую) — каждая
  строка становится отдельным тегом, alias/id и формат тега для всех трёх моделей
  (Illustrious/Anima/Z-Image Turbo) генерируются автоматически из текста строки.
  Чекбоксы управляют включением в реальном времени: можно отключить весь файл целиком или
  отдельную строку, без удаления данных.
  - Бэкенд: `egodary/core/wildcards.py` (парсинг строк, slugify, генерация TagItem),
    новые таблицы `wildcards` / `wildcard_items` в SQLite, теги загружаются в существующий
    `RuntimeRegistry` overlay-механизм (`source="wildcard"`) — генератор видит их как
    обычные теги выбранной категории/подгруппы без какой-либо отдельной логики в pipeline.
  - API: `GET/POST /api/wildcards`, `GET /api/wildcards/{id}`, `POST /api/wildcards/preview`,
    `POST /api/wildcards/{id}/toggle`, `POST /api/wildcards/{id}/items/{item_id}/toggle`,
    `DELETE /api/wildcards/{id}`.
  - UI: новая вкладка «Wildcards» — форма загрузки (выбор category/subgroup, textarea или
    файл .txt, live-preview парсинга), список загруженных файлов со счётчиком строк,
    разворачиваемый построчный список с собственным чекбоксом на каждую строку.

## [0.1.34] — 2026-06-19

### Fixed
- Счётчики выбора в дереве категорий/подгрупп (Pose, Outfit и др.): отображаются при активном выборе; исправлена вложенная кнопка «+», скрывавшая счётчик.

## [0.1.33] — 2026-06-19

### Added
- Кнопка **+** у категорий и подгрупп в дереве тегов (Outfit, Character, Style и др.): открывает Add tag с уже выбранной category/subcategory.

## [0.1.32] — 2026-06-19

### Fixed
- UI: синтаксическая ошибка в `app.js` (обломок кода после правок Tag Studio) — весь интерфейс не инициализировался.

## [0.1.31] — 2026-06-19

### Fixed
- Tag Studio Search: результаты кликабельны — выбор тега из поиска включает Edit/Move/Delete (раньше нужен был только листер).

### Changed
- Tag Studio: tooltips (`title`) на кнопках Search, дедупликации, миграции, листера и действий с тегом; Enter в поле Search запускает поиск.

## [0.1.30] — 2026-06-19

### Changed
- Notes / Todo: компактные строки, узкое поле due date, «Без срока» справа от календаря; кнопка ✓ (выполнено) переносит задачу под активные; удаление с подтверждением.

## [0.1.29] — 2026-06-19

### Fixed
- Tag Studio **Edit tag**: поля снова редактируемые; сохранение core-тега создаёт runtime-копию с тем же id (fork на сервере), без режима «только просмотр».

## [0.1.28] — 2026-06-19

### Changed
- Advanced Todo: выбор **Due date** через календарь (кнопка 📅 + `type="date"`), чекбокс **Без срока** в форме добавления и у каждой задачи в списке.

## [0.1.27] — 2026-06-19

### Fixed
- Tag Studio: **Edit tag** открывает модалку для core-тегов (режим просмотра) и для runtime-тегов (редактирование); раньше кнопка была disabled без обратной связи.

### Changed
- Tag Studio: кнопки **+ Add tag**, **Edit**, **Move**, **Delete** — единый стиль `btn-secondary btn-sm`.

## [0.1.26] — 2026-06-19

### Added
- Accessories: секция **Tattoos & Body Art** — 5 подгрупп (Styles, Placements, Themes, Specific, Temporary), 56 тегов в `appearance.tattoos`.
- Prompt bucket `tattoos` после `outfit` (Illustrious / Anima / Z-Image) — порядок: стиль → placement → тема.

## [0.1.25] — 2026-06-19

### Changed
- Outfit: clothing states привязываются к тегу выбранного предмета в слоте (`pulled down bodycon micro dress`, `pulled down wet bodycon micro dress`), а не как отдельные generic-теги (`clothing pulled down`).
- Каталог `outfit.clothing_state`: короткие modifier-фразы без слова «clothing».

## [0.1.24] — 2026-06-19

### Fixed
- UI: исправлен краш при загрузке — `init()` вызывал удалённую `ensureClothingConditions()` вместо `ensureClothingStateCatalog()`; из-за этого не рендерились панели Style, Character и остальные вкладки.

## [0.1.23] — 2026-06-19

### Changed
- Character v0.1.23: объединены skin-подгруппы в одну секцию **Ethnicity & Skin Tone** (Skin Texture, Skin Details, Body Details); убраны дубли `matte skin` и `beauty marks / moles`.
- Session migration v9: remap удалённых `body_details` id при загрузке сессии.

## [0.1.22] — 2026-06-19

### Added
- Outfit v0.1.22: универсальные **Clothing states** (`outfit.clothing_state`) — 8 комбинируемых групп на слот, Quick states presets, аккордеон UI.
- Tag Studio: модалка **Edit tag** (Model-specific tags), улучшенный поиск по alias, **Reactivate** с путём category/subcategory.
- Advanced: **Notes / Todo** с priority, due date, drag-and-drop и сохранением в SQLite (`GET/PUT /api/advanced/todo`).
- Character library: **переименование** пресета (`PATCH /api/character-library/{id}`).
- Accessories: подгруппы gaming, sport, angelic, demonic, crowns & tiaras, medical, religious.

### Changed
- Face: удалена группа Skin (tone/texture/details); texture & details перенесены в Character → Ethnicity & Skin Tone.
- Session migration v8: перенос `face.skin` → character + новый формат `outfit.conditions`.

### Removed
- Deprecated `outfit.clothing_condition` (per-garment monolithic wear phrases).

## [0.1.21] — 2026-06-18

### Fixed
- UI v0.1.21: после импорта промпта или применения пресета счётчики и chips не показывали выбранные теги (устаревший режим Off перекрывал фактический выбор); нормализация payload face-пресетов.

### Added
- UI v0.1.20: подгруппа **Presets** во всех категориях sidebar — **Built-in presets** (Camera, Lighting) и **Custom presets** (остальные); сохранение/переименование/удаление через `/api/user-presets` по scope.
- Camera UI v0.1.19: пресеты перенесены в дерево категории (**Presets → Built-in / Custom presets**) вместо отдельной карточки с сеткой кнопок.
- Camera v0.1.19: пользовательские camera presets — сохранение текущих тегов, переименование, удаление; API `GET/POST/PUT/DELETE /api/user-presets`.

### Changed
- UI v0.1.20: Lighting presets перенесены из верхней карточки в дерево (**Presets → Built-in / Custom presets**); «My presets» переименованы в **Custom presets**.
- Camera UI v0.1.19: built-in presets (30) отображаются компактным списком; один активный пресет, сброс при ручном изменении тегов.
- Tag Studio v0.1.17: добавлен блок **ТЭГ листер** с фильтрами category/subcategory и списком тегов выбранной группы.
- Tag Studio v0.1.17: для выбранного runtime-тега добавлены действия из UI — удалить (confirm), изменить description, перенести в другую category/subcategory.
- Tag Studio v0.1.16: результаты Search/Dedupe/Migration/Rollback теперь выводятся в человеко-читаемом формате со сводкой, бейджами и списком вместо сырого JSON.
- Tag Studio v0.1.16: список найденных тегов оформлен как `ТЕГ — category — subcategory`, добавлены счётчики категорий, подгрупп и aliases.
- UI v0.1.15: кнопка `+ Add tag` перенесена из общего header в секции **Prompting** и **Tag Studio**.
- Tag Studio v0.1.15: добавлен встроенный справочный блок с описанием полей и кнопок (Search, dedupe, migration, rollback, add tag).
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
- API/UI v0.1.17: `GET /api/tag-studio/items` теперь корректно помечает overlay-элементы (`overlay: true/false`), чтобы операции редактирования/перемещения/удаления применялись только к runtime-тегам.
- API v0.1.16: `GET /api/tag-studio/deduplicate` возвращает `source_subcategory` и `match_subcategory`, чтобы UI мог наглядно показывать дубли с подгруппами.
- Add tag v0.1.15: выбор подкатегории в модалке теперь собирается из API и структуры UI, поэтому для `environment.location` всегда доступны целевые subcategory (`indoor`, `outdoor_semi`, `fantasy_stylized`).
- Add tag v0.1.15: для категорий с подкатегориями сохранение без `Subcategory` блокируется в UI, чтобы новый тег сразу появлялся в нужной группе выбора.
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
