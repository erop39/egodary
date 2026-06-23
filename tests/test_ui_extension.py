"""Тесты механизма ui_extension и плагина advanced_prompting."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Добавляем plugins_user в путь для импорта плагина
_PLUGIN_DIR = Path(__file__).resolve().parents[1] / "plugins_user" / "advanced_prompting"
_PLUGIN_PKG = str(_PLUGIN_DIR)
if _PLUGIN_PKG not in sys.path:
    sys.path.insert(0, _PLUGIN_PKG)


# ---------------------------------------------------------------------------
# Тесты протокола UiExtensionPlugin
# ---------------------------------------------------------------------------

class TestUiExtensionProtocol:
    def test_plugin_implements_protocol(self):
        from advanced_prompting.plugin import plugin
        from egodary.plugins.base import UiExtensionPlugin

        assert isinstance(plugin, UiExtensionPlugin)
        assert plugin.id == "advanced_prompting"
        assert callable(plugin.register)

    def test_register_adds_router(self):
        from advanced_prompting.plugin import plugin

        app = MagicMock()
        plugin.register(app)
        # include_router должен быть вызван
        app.include_router.assert_called_once()

    def test_register_mounts_static_if_dir_exists(self):
        from advanced_prompting.plugin import plugin, _STATIC_DIR

        if not _STATIC_DIR.is_dir():
            pytest.skip("static dir not present")

        app = MagicMock()
        plugin.register(app)
        app.mount.assert_called_once()


# ---------------------------------------------------------------------------
# Тесты загрузчика плагинов для ui_extension
# ---------------------------------------------------------------------------

class TestLoaderUiExtension:
    def test_loader_loads_ui_extension(self, tmp_path):
        """Загрузчик корректно загружает ui_extension плагин."""
        from egodary.plugins.loader import PluginManager
        from egodary.core.registry import TagRegistry

        # Используем реальный плагин из plugins_user
        plugins_user = Path(__file__).resolve().parents[1] / "plugins_user"
        builtin = Path(__file__).resolve().parents[1] / "egodary" / "content"

        registry = TagRegistry()
        pm = PluginManager(builtin_dir=builtin, dropin_dir=plugins_user)
        pm.load_all(registry)

        loaded_ids = [p.manifest.plugin.id for p in pm.loaded]
        assert "advanced_prompting" in loaded_ids

        adv = next(p for p in pm.loaded if p.manifest.plugin.id == "advanced_prompting")
        assert adv.ui_extension_instance is not None
        assert adv.ui_extension_instance.id == "advanced_prompting"

    def test_register_ui_extensions_calls_register(self):
        from egodary.plugins.loader import PluginManager, LoadedPlugin
        from egodary.plugins.manifest import PluginManifest, PluginInfo, ContentSection, CodeSection
        from egodary.plugins.base import PluginKind

        # Создаём mock-плагин
        mock_instance = MagicMock()
        mock_instance.id = "test_ui"

        manifest = PluginManifest(
            plugin=PluginInfo(id="test_ui", name="Test UI", version="0.1.0", kind=PluginKind.UI_EXTENSION),
            content=ContentSection(),
            code=CodeSection(),
        )
        loaded = LoadedPlugin(manifest=manifest, source="test", ui_extension_instance=mock_instance)

        pm = PluginManager(builtin_dir=Path("."), dropin_dir=Path("."))
        pm.loaded = [loaded]

        app = MagicMock()
        registered = pm.register_ui_extensions(app)

        assert registered == ["test_ui"]
        mock_instance.register.assert_called_once_with(app)

    def test_register_ui_extensions_skips_non_ui(self):
        from egodary.plugins.loader import PluginManager, LoadedPlugin
        from egodary.plugins.manifest import PluginManifest, PluginInfo, ContentSection, CodeSection
        from egodary.plugins.base import PluginKind

        manifest = PluginManifest(
            plugin=PluginInfo(id="content_only", name="Content", version="0.1.0", kind=PluginKind.CONTENT_PACK),
            content=ContentSection(),
            code=CodeSection(),
        )
        loaded = LoadedPlugin(manifest=manifest, source="test", ui_extension_instance=None)

        pm = PluginManager(builtin_dir=Path("."), dropin_dir=Path("."))
        pm.loaded = [loaded]

        app = MagicMock()
        registered = pm.register_ui_extensions(app)
        assert registered == []

    def test_register_ui_extensions_survives_plugin_error(self):
        """Ошибка в register() плагина не роняет сервер."""
        from egodary.plugins.loader import PluginManager, LoadedPlugin
        from egodary.plugins.manifest import PluginManifest, PluginInfo, ContentSection, CodeSection
        from egodary.plugins.base import PluginKind

        broken_instance = MagicMock()
        broken_instance.id = "broken"
        broken_instance.register.side_effect = RuntimeError("oops")

        manifest = PluginManifest(
            plugin=PluginInfo(id="broken", name="Broken", version="0.1.0", kind=PluginKind.UI_EXTENSION),
            content=ContentSection(),
            code=CodeSection(),
        )
        loaded = LoadedPlugin(manifest=manifest, source="test", ui_extension_instance=broken_instance)

        pm = PluginManager(builtin_dir=Path("."), dropin_dir=Path("."))
        pm.loaded = [loaded]

        app = MagicMock()
        registered = pm.register_ui_extensions(app)  # не должен падать
        assert registered == []  # зарегистрирован не был


# ---------------------------------------------------------------------------
# Тесты API роутов плагина
# ---------------------------------------------------------------------------

class TestAdvancedPromptingRoutes:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from advanced_prompting.plugin import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_info(self, client):
        r = client.get("/api/advanced-prompting/info")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == "advanced_prompting"
        assert "bucket_order" in data
        assert "quality" in data["bucket_order"]

    def test_rebuild_basic(self, client):
        r = client.post("/api/advanced-prompting/rebuild", json={
            "blocks": [
                {"name": "quality", "tags": ["best quality", "masterpiece"]},
                {"name": "character", "tags": ["1girl", "solo"]},
            ],
            "model_id": "illustrious",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["positive"] == "best quality, masterpiece, 1girl, solo"

    def test_rebuild_empty_tags_skipped(self, client):
        r = client.post("/api/advanced-prompting/rebuild", json={
            "blocks": [
                {"name": "quality", "tags": ["best quality", "", "  "]},
                {"name": "pose", "tags": []},
            ],
        })
        assert r.status_code == 200
        assert r.json()["positive"] == "best quality"

    def test_rebuild_preserves_block_order(self, client):
        r = client.post("/api/advanced-prompting/rebuild", json={
            "blocks": [
                {"name": "style", "tags": ["anime style"]},
                {"name": "quality", "tags": ["best quality"]},
            ],
        })
        assert r.status_code == 200
        # style идёт первым — порядок из запроса
        assert r.json()["positive"] == "anime style, best quality"

    def test_from_generate_orders_buckets(self, client):
        r = client.post("/api/advanced-prompting/from-generate", json={
            "style": ["anime style"],
            "quality": ["best quality"],
            "character": ["1girl"],
        })
        assert r.status_code == 200
        blocks = r.json()["blocks"]
        names = [b["name"] for b in blocks]
        # quality должен идти раньше style согласно BUCKET_ORDER
        assert names.index("quality") < names.index("style")
        assert "character" in names

    def test_from_generate_skips_empty_buckets(self, client):
        r = client.post("/api/advanced-prompting/from-generate", json={
            "quality": ["best quality"],
            "pose": [],
            "face": [],
        })
        assert r.status_code == 200
        names = [b["name"] for b in r.json()["blocks"]]
        assert "quality" in names
        assert "pose" not in names
        assert "face" not in names

    def test_rebuild_returns_blocks(self, client):
        blocks_in = [{"name": "quality", "tags": ["best quality"]}]
        r = client.post("/api/advanced-prompting/rebuild", json={"blocks": blocks_in})
        assert r.status_code == 200
        assert r.json()["blocks"] == blocks_in


# ---------------------------------------------------------------------------
# Тесты /api/plugins эндпоинтов
# ---------------------------------------------------------------------------

class TestPluginsApi:
    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        """TestClient с временным dropin_dir."""
        import egodary.api.main as main_mod
        monkeypatch.setattr(main_mod, "_get_dropin_dir", lambda: tmp_path)
        from fastapi.testclient import TestClient
        client = TestClient(main_mod.app)
        yield client, tmp_path

    def test_plugins_list_empty(self, client):
        c, _ = client
        r = c.get("/api/plugins")
        assert r.status_code == 200
        assert r.json()["plugins"] == []

    def test_plugins_list_shows_manifest(self, client):
        c, tmp_path = client
        plugin_dir = tmp_path / "my_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "manifest.toml").write_text(
            '[plugin]\nid="my_plugin"\nname="My Plugin"\nversion="1.0.0"\nkind="ui_extension"\n'
        )
        r = c.get("/api/plugins")
        assert r.status_code == 200
        plugins = r.json()["plugins"]
        assert len(plugins) == 1
        assert plugins[0]["id"] == "my_plugin"
        assert plugins[0]["enabled"] is True

    def test_plugins_list_shows_disabled(self, client):
        c, tmp_path = client
        plugin_dir = tmp_path / "my_plugin.disabled"
        plugin_dir.mkdir()
        (plugin_dir / "manifest.toml").write_text(
            '[plugin]\nid="my_plugin"\nname="My Plugin"\nversion="1.0.0"\nkind="ui_extension"\n'
        )
        r = c.get("/api/plugins")
        plugins = r.json()["plugins"]
        assert plugins[0]["enabled"] is False

    def test_plugin_disable(self, client):
        c, tmp_path = client
        plugin_dir = tmp_path / "my_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "manifest.toml").write_text(
            '[plugin]\nid="my_plugin"\nname="My Plugin"\nversion="1.0.0"\nkind="ui_extension"\n'
        )
        r = c.post("/api/plugins/my_plugin/disable")
        assert r.status_code == 200
        assert r.json()["enabled"] is False
        assert (tmp_path / "my_plugin.disabled").exists()
        assert not (tmp_path / "my_plugin").exists()

    def test_plugin_enable(self, client):
        c, tmp_path = client
        plugin_dir = tmp_path / "my_plugin.disabled"
        plugin_dir.mkdir()
        (plugin_dir / "manifest.toml").write_text(
            '[plugin]\nid="my_plugin"\nname="My Plugin"\nversion="1.0.0"\nkind="ui_extension"\n'
        )
        r = c.post("/api/plugins/my_plugin/enable")
        assert r.status_code == 200
        assert r.json()["enabled"] is True
        assert (tmp_path / "my_plugin").exists()
        assert not (tmp_path / "my_plugin.disabled").exists()

    def test_plugin_disable_not_found(self, client):
        c, _ = client
        r = c.post("/api/plugins/nonexistent/disable")
        assert r.status_code == 404

    def test_plugin_enable_not_found(self, client):
        c, _ = client
        r = c.post("/api/plugins/nonexistent/enable")
        assert r.status_code == 404
