# Transfer Guide (handoff)

Документ для безопасного переноса проекта на другую машину/среду.

## 1) Что передавать

- Весь репозиторий `egodary`.
- Не передавать локальные артефакты:
  - `.venv/`, `venv/`
  - `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`
  - `*.db`, `*.sqlite3`
  - `release/` (если не нужен старый архив)

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

## 5) Smoke-check после запуска

- `GET /api/health` возвращает `{"status":"ok"}`.
- В UI вкладки и чипы загружаются без ошибок.
- Preview/Generate работают, в `Results` отображаются теги.
- Сохранение/загрузка Character Library работает.

## 6) Частые проблемы

- `{"detail":"Not Found"}` на главной: занят порт старым uvicorn-процессом.
- Некорректные старые значения в браузере: сделать `Ctrl+F5` и при необходимости сбросить сессию в UI.
- После обновления каталогов не видно новые тултипы: запустить `scripts/build_tag_tooltips_ru.py`.
