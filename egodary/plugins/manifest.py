"""Схема `manifest.toml` и его разбор.

Формат соответствует разделу 4.2 плана разработки. На фазе 1 реально
используются поля для `content_pack`; поля для других видов плагинов
(`module`, `entry`) уже описаны в схеме, чтобы не менять формат файла
повторно в фазе 4+ — но загрузчик их пока не исполняет.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from egodary.plugins.base import PluginKind


class PluginInfo(BaseModel):
    id: str
    name: str
    version: str
    kind: PluginKind
    author: str = ""
    requires_core: str = "*"
    depends_on: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _id_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("plugin.id не может быть пустым")
        return value


class ContentSection(BaseModel):
    tags_file: str | None = None
    tags_dir: str | None = None
    conflicts_file: str | None = None


class CodeSection(BaseModel):
    """Для kind != content_pack: путь к модулю и имени объекта/класса,
    реализующего соответствующий протокол. Не используется в фазе 1.
    """

    module: str | None = None
    entry: str | None = None


class PluginManifest(BaseModel):
    plugin: PluginInfo
    content: ContentSection = ContentSection()
    code: CodeSection = CodeSection()


def parse_manifest(manifest_path: Path) -> PluginManifest:
    raw = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    return PluginManifest.model_validate(raw)
