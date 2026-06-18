# plugins_user

Сюда кладутся личные/сторонние content-пак плагины — drop-in, без установки
через pip. Формат — см. `egodary/content/core_time_weather/` как живой
пример (`manifest.toml` + `tags.yaml`).

Минимальная структура одного плагина:

```
plugins_user/
└── my_pack/
    ├── manifest.toml
    └── tags.yaml
```

Загружаются автоматически при старте (`PluginManager.load_all`). Дублирующийся
id категории или тега между паками — явная ошибка при загрузке, а не
молчаливая перезапись.
