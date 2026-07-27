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

    # frob:tests tests/unit/fleet/test_manifest.py::TestLoadManifest.test_relative_path_resolves_against_manifest_dir_not_cwd  # noqa: E501
    def test_relative_path_resolves_against_manifest_dir_not_cwd(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """T-1023 (INV-046): a relative `path=` entry must resolve against
        the MANIFEST FILE's own directory, regardless of the process cwd
        at load time -- `test_load_manifest_ok` above never actually
        varies cwd from the manifest's own directory, so it cannot
        distinguish "rebased against manifest dir" from "rebased against
        cwd" (they coincide there); this test puts cwd somewhere ELSE
        entirely to prove the two are not conflated."""
        manifest_dir = tmp_path / "repos" / "frob"
        manifest_dir.mkdir(parents=True)
        manifest_path = manifest_dir / "fleet.toml"
        manifest_path.write_text('[[repo]]\nname = "sibling"\npath = "../typani"\n')
        elsewhere = tmp_path / "somewhere-else"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)

        result = load_manifest(manifest_path)

        assert result.is_ok
        resolved = result.danger_ok.repos[0].path
        assert resolved == (manifest_dir / "../typani")
        assert elsewhere not in resolved.parents

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
