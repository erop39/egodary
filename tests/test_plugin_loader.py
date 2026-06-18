from pathlib import Path

import pytest

from egodary.bootstrap import build_app
from egodary.core.registry import TagRegistry
from egodary.plugins.loader import PluginLoadError, PluginManager


def _write_plugin(
    root: Path,
    plugin_id: str,
    *,
    category_id: str,
    depends_on: list[str] | None = None,
    requires_core: str = "*",
) -> None:
    plugin_dir = root / plugin_id
    plugin_dir.mkdir(parents=True)
    depends_toml = repr(depends_on or [])
    (plugin_dir / "manifest.toml").write_text(
        f"""
        [plugin]
        id = "{plugin_id}"
        name = "{plugin_id}"
        version = "1.0.0"
        kind = "content_pack"
        requires_core = "{requires_core}"
        depends_on = {depends_toml}

        [content]
        tags_file = "tags.yaml"
        """,
        encoding="utf-8",
    )
    (plugin_dir / "tags.yaml").write_text(
        f"""
        categories:
          - id: {category_id}
            title: "{category_id}"
            items:
              - id: only_item
                label: "Only Item"
                tags:
                  illustrious: "only item tag"
        """,
        encoding="utf-8",
    )


def test_tags_dir_format_loads_multiple_categories(tmp_path: Path) -> None:
    """Паки с content.tags_dir (несколько *.yaml) не должны ломать build_app."""
    builtin_dir = tmp_path / "content"
    plugin_dir = builtin_dir / "multi_yaml_pack"
    tags_dir = plugin_dir / "tags"
    tags_dir.mkdir(parents=True)
    (plugin_dir / "manifest.toml").write_text(
        """
        [plugin]
        id = "multi_yaml_pack"
        name = "Multi YAML"
        version = "1.0.0"
        kind = "content_pack"
        requires_core = "*"
        depends_on = []

        [content]
        tags_dir = "tags"
        """,
        encoding="utf-8",
    )
    (tags_dir / "a.yaml").write_text(
        """
        id: demo.a
        title: "A"
        items:
          - id: one
            label: "One"
            tags:
              illustrious: "one"
        """,
        encoding="utf-8",
    )
    (tags_dir / "b.yaml").write_text(
        """
        id: demo.b
        title: "B"
        items:
          - id: two
            label: "Two"
            tags:
              illustrious: "two"
        """,
        encoding="utf-8",
    )

    registry = TagRegistry()
    manager = PluginManager(builtin_dir=builtin_dir, dropin_dir=tmp_path / "empty_dropin")
    manager.load_all(registry)

    assert registry.get_category("demo.a") is not None
    assert registry.get_category("demo.b") is not None


def test_rules_pack_directory_does_not_break_plugin_loader(tmp_path: Path) -> None:
    """rules_pack is loaded by rules_loader, not the content plugin pipeline."""
    builtin_dir = tmp_path / "content"
    rules_dir = builtin_dir / "rules_pack"
    rules_dir.mkdir(parents=True)
    (rules_dir / "manifest.toml").write_text(
        """
        [plugin]
        id = "rules_pack"
        name = "Rules Pack"
        version = "1.0.0"
        kind = "rules_pack"
        requires_core = "*"
        depends_on = []
        """,
        encoding="utf-8",
    )
    _write_plugin(builtin_dir, "demo_pack", category_id="demo.rules_ok")

    registry = TagRegistry()
    manager = PluginManager(builtin_dir=builtin_dir, dropin_dir=tmp_path / "empty_dropin")
    manager.load_all(registry)

    assert registry.get_category("demo.rules_ok") is not None
    assert not any(p["id"] == "rules_pack" for p in manager.summary()["loaded"])


def test_real_builtin_core_time_weather_pack_loads() -> None:
    """Сквозная проверка реального встроенного пака (фаза 1, проверка формата на практике)."""
    registry, plugin_manager = build_app()

    assert "scene.time_of_day" in registry.category_ids()
    assert "scene.weather" in registry.category_ids()
    assert "scene.time" in registry.category_ids()

    time_category = registry.get_category("scene.time_of_day")
    assert time_category is not None
    assert len(time_category.items) == 8  # sunrise..midnight

    summary = plugin_manager.summary()
    assert any(p["id"] == "core_time_weather" for p in summary["loaded"])


def test_dropin_plugin_loads_alongside_builtin(tmp_path: Path) -> None:
    dropin_dir = tmp_path / "plugins_user"
    dropin_dir.mkdir()
    _write_plugin(dropin_dir, "demo_dropin", category_id="demo.category")

    registry = TagRegistry()
    manager = PluginManager(builtin_dir=tmp_path / "empty_builtin", dropin_dir=dropin_dir)
    manager.load_all(registry)

    assert registry.get_category("demo.category") is not None
    assert manager.summary()["loaded"][0]["source"] == "dropin"


def test_duplicate_category_id_across_plugins_raises(tmp_path: Path) -> None:
    dropin_dir = tmp_path / "plugins_user"
    dropin_dir.mkdir()
    _write_plugin(dropin_dir, "pack_one", category_id="shared.category")
    _write_plugin(dropin_dir, "pack_two", category_id="shared.category")

    registry = TagRegistry()
    manager = PluginManager(builtin_dir=tmp_path / "empty_builtin", dropin_dir=dropin_dir)

    with pytest.raises(PluginLoadError):
        manager.load_all(registry)


def test_unsatisfied_version_requirement_raises(tmp_path: Path) -> None:
    dropin_dir = tmp_path / "plugins_user"
    dropin_dir.mkdir()
    _write_plugin(dropin_dir, "too_new", category_id="demo.category", requires_core="999.0.0")

    registry = TagRegistry()
    manager = PluginManager(builtin_dir=tmp_path / "empty_builtin", dropin_dir=dropin_dir)

    with pytest.raises(PluginLoadError):
        manager.load_all(registry)


def test_missing_dependency_raises(tmp_path: Path) -> None:
    dropin_dir = tmp_path / "plugins_user"
    dropin_dir.mkdir()
    _write_plugin(dropin_dir, "needs_ghost", category_id="demo.category", depends_on=["ghost_plugin"])

    registry = TagRegistry()
    manager = PluginManager(builtin_dir=tmp_path / "empty_builtin", dropin_dir=dropin_dir)

    with pytest.raises(PluginLoadError):
        manager.load_all(registry)
