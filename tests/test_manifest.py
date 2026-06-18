from pathlib import Path

import pytest

from egodary.plugins.manifest import parse_manifest


def test_parse_manifest_content_pack(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.toml"
    manifest_path.write_text(
        """
        [plugin]
        id = "demo_pack"
        name = "Demo Pack"
        version = "1.0.0"
        kind = "content_pack"
        requires_core = ">=0.1.0"

        [content]
        tags_file = "tags.yaml"
        """,
        encoding="utf-8",
    )

    manifest = parse_manifest(manifest_path)

    assert manifest.plugin.id == "demo_pack"
    assert manifest.plugin.kind.value == "content_pack"
    assert manifest.content.tags_file == "tags.yaml"
    assert manifest.content.conflicts_file is None


def test_parse_manifest_rejects_empty_id(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.toml"
    manifest_path.write_text(
        """
        [plugin]
        id = ""
        name = "Broken"
        version = "1.0.0"
        kind = "content_pack"
        """,
        encoding="utf-8",
    )

    with pytest.raises(Exception):
        parse_manifest(manifest_path)
