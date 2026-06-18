"""Протоколы плагинов.

На этой фазе (1) полностью реализована поддержка `content_pack` — она не
требует Python-кода от автора плагина, только `manifest.toml` + `tags.yaml`
(см. `egodary/content/core_time_weather` как живой пример). Остальные виды
плагинов — заготовки на будущее, чтобы манифест и `PluginKind` сразу были
рассчитаны на них и не пришлось менять формат при добавлении:

- `model_adapter` — фаза 4–5 (Illustrious/Anima/Z-Image Turbo);
- `pipeline_stage` — фаза 6–7 (свои конфликты/скоринг/рандомайзер);
- `integration` — фаза 11 (Forge/ComfyUI);
- `ui_extension` — фаза 10.
"""

from __future__ import annotations

from enum import Enum
from typing import Protocol, runtime_checkable

from egodary.core.models import TagCategory


class PluginKind(str, Enum):
    CONTENT_PACK = "content_pack"
    RULES_PACK = "rules_pack"
    MODEL_ADAPTER = "model_adapter"
    PIPELINE_STAGE = "pipeline_stage"
    INTEGRATION = "integration"
    UI_EXTENSION = "ui_extension"


@runtime_checkable
class ContentPackPlugin(Protocol):
    """Точка расширения для контент-паков, которым нужна не только статичная
    YAML-загрузка, а вычисляемые/программные категории. Для большинства
    паков (просто список тегов) это не нужно — достаточно `tags.yaml`,
    который загрузчик читает сам, без обращения к этому протоколу.
    """

    id: str

    def get_categories(self) -> list[TagCategory]: ...


@runtime_checkable
class PipelineStagePlugin(Protocol):
    """Заготовка на фазу 6–7: хук в конвейер сборки промпта."""

    id: str
    stage: str

    def process(self, buckets: dict, context: dict) -> dict: ...


@runtime_checkable
class IntegrationPlugin(Protocol):
    """Заготовка на фазу 11: отправка готового промпта во внешнюю систему."""

    id: str

    def send(self, prompt: str, params: dict) -> dict: ...
