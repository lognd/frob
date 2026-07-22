"""Unit tests for frob.fleet manifest loading (docs/modules/fleet.md#manifest)."""

from __future__ import annotations

from pathlib import Path

from frob.fleet import FleetError, load_manifest


class TestLoadManifest:
    def test_load_manifest_ok(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "fleet.toml"
        manifest_path.write_text(
            '[[repo]]\nname = "a"\npath = "../a"\n'
            '\n[[repo]]\nname = "b"\npath = "/abs/b"\n'
        )
        result = load_manifest(manifest_path)
        assert result.is_ok
        manifest = result.danger_ok
        assert [r.name for r in manifest.repos] == ["a", "b"]
        # relative path rebased against the manifest file's own directory
        assert manifest.repos[0].path == (tmp_path / "../a")
        # already-absolute path left untouched
        assert manifest.repos[1].path == Path("/abs/b")

    def test_load_manifest_missing(self, tmp_path: Path) -> None:
        result = load_manifest(tmp_path / "does-not-exist.toml")
        assert result.is_err
        assert result.danger_err is FleetError.ManifestNotFound

    def test_load_manifest_malformed(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "fleet.toml"
        manifest_path.write_text("not valid toml [[[")
        result = load_manifest(manifest_path)
        assert result.is_err
        assert result.danger_err is FleetError.ManifestMalformed
