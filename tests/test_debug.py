from egodary.bootstrap import build_app
from egodary.core.debug import get_debug_snapshot


def test_debug_snapshot_has_expected_keys() -> None:
    registry, plugin_manager = build_app()
    snapshot = get_debug_snapshot(registry, plugin_manager)

    assert snapshot["app_version"]
    assert snapshot["build_number"]
    assert "plugins" in snapshot
    assert "registry" in snapshot
    assert snapshot["registry"]["category_count"] >= 2
    assert "category_prefixes" in snapshot
