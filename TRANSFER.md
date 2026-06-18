# Transfer Guide (handoff)

Документ для безопасного переноса проекта на другую машину/среду.

## 1) Что передавать

- Весь репозиторий `egodary` **или** готовый архив из `prepare_transfer.bat`.
- Опционально (если нужны сохранённые данные с текущего ПК):
  - `egodary.db` — избранное, Character Library, user presets (Camera/Lighting и др.), история генераций, runtime-теги Tag Studio, LLM settings.
  - `rules_user/` — пользовательские правила моделей (например профиль Anima).
  - `plugins_user/` — личные content-паки (drop-in).
  - `config.toml` — если создавали локальный конфиг (путь по умолчанию: корень репозитория).
- Не передавать локальные артефакты:
  - `.venv/`, `venv/`
  - `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`
  - `*.db`, `*.sqlite3` *(кроме случая, когда сознательно переносите `egodary.db`)*
  - `release/` (если не нужен старый архив)
  - `.cursor/`, `.idea/`, `.vscode/`

## 2) Автоматическая подготовка архива

Из корня проекта:

```bat
prepare_transfer.bat
```

Скрипт:
- обновляет зависимости;
- пересобирает каталоги;
- запускает `ruff` и `pytest`;
- создаёт архив `release/egodary-transfer-YYYYMMDD-HHMM.zip`.

## 3) Подготовка целевой машины

- Python `3.11+`
- доступ к `pip`

Рекомендуется (Windows):

```bat
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## 4) Первый запуск после переноса

```bat
update_and_run.bat
```

Или вручную:

```bash
python scripts/build_tag_tooltips_ru.py
python -m pytest -q
python -m egodary.cli.main serve
```

UI: `http://127.0.0.1:8000/`

## 5) Перенос пользовательских данных (опционально)

Если на старом ПК уже есть `egodary.db`, скопируйте файл в **корень** репозитория на новом ПК **до** первого запуска сервера (или замените после остановки uvicorn). База создаётся автоматически при старте, если файла нет.

Таблицы в `egodary.db`: favorites, character_presets, user_presets, model_profiles, generation_history, unknown_tags, llm_settings и др.

Аналогично скопируйте `rules_user/` и `plugins_user/`, если там есть ваши правки.

## 6) Smoke-check после запуска

- `GET /api/health` возвращает `{"status":"ok"}`.
- В UI вкладки и чипы загружаются без ошибок.
- Preview/Generate работают, в `Results` отображаются теги.
- Сохранение/загрузка Character Library работает.
- Custom presets (Camera, Lighting и др.) видны в sidebar → **Presets → Custom presets**.
- Tag Studio: поиск тегов и Add tag работают.

## 7) Частые проблемы

- `{"detail":"Not Found"}` на главной: занят порт старым uvicorn-процессом.
- Некорректные старые значения в браузере: сделать `Ctrl+F5` и при необходимости сбросить сессию в UI.
- После обновления каталогов не видно новые тултипы: запустить `scripts/build_tag_tooltips_ru.py`.
