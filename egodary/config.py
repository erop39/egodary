"""Application configuration via pydantic-settings."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict
from pydantic_settings.sources import TomlConfigSettingsSource

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
DEFAULT_CONTENT_DIR = PACKAGE_ROOT / "content"
DEFAULT_PLUGINS_USER_DIR = PROJECT_ROOT / "plugins_user"
DEFAULT_RULES_USER_DIR = PROJECT_ROOT / "rules_user"


class EgodarySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EGODARY_",
        env_nested_delimiter="__",
        toml_file="config.toml",
    )

    plugins_user_dir: Path = Field(default=DEFAULT_PLUGINS_USER_DIR)
    rules_user_dir: Path = Field(default=DEFAULT_RULES_USER_DIR)
    content_dir: Path = Field(default=DEFAULT_CONTENT_DIR)
    enabled_plugins: list[str] = Field(
        default_factory=lambda: ["core_tags", "outfit_pack", "scene_location_pack", "pose_pack", "fetish_pack"]
    )
    default_model: str = "illustrious"
    log_level: str = "INFO"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            TomlConfigSettingsSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )


def get_settings() -> EgodarySettings:
    return EgodarySettings()
