"""frob.release: mechanical semver from the public-API graph (T-0003)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from frob.graph import build_graph
from frob.release import (
    BumpClass,
    ReleaseError,
    authoritative_version,
    changelog_skeleton_entry,
    diff_class,
    load_manifest,
    manifest_path,
    required_version,
    rewrite_pyproject_version,
    satisfies,
    set_manifest_version,
    stamp,
)


def _snap(root: Path):
    return build_graph(root, root / ".frob" / "cache.db").danger_ok


def _write(root: Path, body: str) -> None:
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "m.py").write_text(body, encoding="utf-8")


def test_stamp_and_no_change_is_none(tmp_path):
    # frob:tests src/frob/release/__init__.py::stamp
    _write(tmp_path, "def public(x: int) -> int:\n    return x\n")
    stamp(tmp_path, _snap(tmp_path), "1.0.0")
    assert load_manifest(tmp_path).danger_ok.version == "1.0.0"
    assert (
        diff_class(load_manifest(tmp_path).danger_ok, _snap(tmp_path)) == BumpClass.NONE
    )


def test_new_public_symbol_is_minor(tmp_path):
    # frob:tests src/frob/release/__init__.py::diff_class
    _write(tmp_path, "def a(x: int) -> int:\n    return x\n")
    stamp(tmp_path, _snap(tmp_path), "1.0.0")
    manifest = load_manifest(tmp_path).danger_ok
    _write(
        tmp_path, "def a(x: int) -> int:\n    return x\ndef b() -> int:\n    return 0\n"
    )
    (tmp_path / ".frob" / "cache.db").unlink()
    assert diff_class(manifest, _snap(tmp_path)) == BumpClass.MINOR


def test_changed_signature_is_major(tmp_path):
    _write(tmp_path, "def a(x: int) -> int:\n    return x\n")
    stamp(tmp_path, _snap(tmp_path), "1.0.0")
    manifest = load_manifest(tmp_path).danger_ok
    _write(tmp_path, "def a(x: int, y: int) -> int:\n    return x + y\n")
    (tmp_path / ".frob" / "cache.db").unlink()
    assert diff_class(manifest, _snap(tmp_path)) == BumpClass.MAJOR


def test_manifest_path_is_root_relative(tmp_path):
    # frob:tests src/frob/release/__init__.py::manifest_path kind="unit"
    assert manifest_path(tmp_path) == tmp_path / ".frob-release.json"


def test_load_manifest_missing_is_no_manifest(tmp_path):
    # frob:tests src/frob/release/__init__.py::load_manifest kind="unit"
    result = load_manifest(tmp_path)
    assert result.is_err
    assert result.danger_err == ReleaseError.NoManifest


def test_load_manifest_reads_stamped_version(tmp_path):
    # frob:tests src/frob/release/__init__.py::load_manifest kind="unit"
    _write(tmp_path, "def public(x: int) -> int:\n    return x\n")
    stamp(tmp_path, _snap(tmp_path), "1.0.0")
    manifest = load_manifest(tmp_path).danger_ok
    assert manifest.version == "1.0.0"
    assert any("public" in ref for ref in manifest.api)


def test_required_version_and_satisfies():
    assert required_version("1.2.3", BumpClass.MAJOR).danger_ok == "2.0.0"
    assert required_version("1.2.3", BumpClass.MINOR).danger_ok == "1.3.0"
    assert required_version("1.2.3", BumpClass.PATCH).danger_ok == "1.2.4"
    assert satisfies("2.0.0", "2.0.0")
    assert not satisfies("1.9.9", "2.0.0")


# frob:ticket T-1281
def test_load_manifest_malformed_json_is_err(tmp_path):
    # frob:tests src/frob/release/__init__.py::load_manifest
    manifest_path(tmp_path).write_text("{not valid json", encoding="utf-8")
    result = load_manifest(tmp_path)
    assert result.is_err
    assert result.danger_err == ReleaseError.Malformed


# frob:ticket T-1281
def test_required_version_bad_previous_is_err():
    # frob:tests src/frob/release/__init__.py::required_version
    result = required_version("not-a-version", BumpClass.PATCH)
    assert result.is_err
    assert result.danger_err == ReleaseError.BadVersion


# frob:ticket T-1281
def test_satisfies_unparseable_inputs_are_false():
    # frob:tests src/frob/release/__init__.py::satisfies
    assert satisfies("garbage", "1.0.0") is False
    assert satisfies("1.0.0", "garbage") is False


# frob:ticket T-1281
class TestSetManifestVersion:
    """T-1078/T-1281: resync ONLY the manifest's version field, in place."""

    def test_rewrites_version_preserving_api(self, tmp_path):
        # frob:tests src/frob/release/__init__.py::set_manifest_version
        _write(tmp_path, "def a(x: int) -> int:\n    return x\n")
        stamp(tmp_path, _snap(tmp_path), "1.0.0")
        original_api = load_manifest(tmp_path).danger_ok.api
        result = set_manifest_version(tmp_path, "2.0.0")
        assert result.danger_ok == "2.0.0"
        updated = load_manifest(tmp_path).danger_ok
        assert updated.version == "2.0.0"
        assert updated.api == original_api

    def test_no_manifest_is_err(self, tmp_path):
        # frob:tests src/frob/release/__init__.py::set_manifest_version
        result = set_manifest_version(tmp_path, "2.0.0")
        assert result.is_err
        assert result.danger_err == ReleaseError.NoManifest

    def test_malformed_manifest_is_err(self, tmp_path):
        # frob:tests src/frob/release/__init__.py::set_manifest_version
        manifest_path(tmp_path).write_text("{not valid json", encoding="utf-8")
        result = set_manifest_version(tmp_path, "2.0.0")
        assert result.is_err
        assert result.danger_err == ReleaseError.Malformed


def test_breaking_change_in_0x_bumps_minor_not_to_1_0_0():
    # semver section 4: in 0.y.z a breaking change bumps the MINOR, it must
    # NOT force 1.0.0 -- committing to 1.0.0 is a deliberate stability choice.
    assert required_version("0.10.0", BumpClass.MAJOR).danger_ok == "0.11.0"
    assert required_version("0.1.0", BumpClass.MAJOR).danger_ok == "0.2.0"
    assert required_version("0.10.0", BumpClass.MINOR).danger_ok == "0.11.0"
    # once at >=1.0.0, a breaking change DOES bump the major
    assert required_version("1.0.0", BumpClass.MAJOR).danger_ok == "2.0.0"


def test_release_gate_flags_missing_bump(tmp_path):
    # frob:tests src/frob/gates/__init__.py::release_gate
    # frob:tests src/frob/release kind="integration"
    # Drives frob.release's manifest loading, snapshot diffing, and required
    # version/satisfies check together through the real release_gate caller.
    from frob.gates import release_gate

    _write(tmp_path, "def a(x: int) -> int:\n    return x\n")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "p"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    stamp(tmp_path, _snap(tmp_path), "1.0.0")
    # breaking change, version still 1.0.0
    _write(tmp_path, "def a(x: str) -> str:\n    return x\n")
    (tmp_path / ".frob" / "cache.db").unlink()
    violations = release_gate(tmp_path, _snap(tmp_path))
    assert any(v.rule == "REL001" and "2.0.0" in v.message for v in violations)


def test_release_gate_skips_without_manifest(tmp_path):
    from frob.gates import release_gate

    _write(tmp_path, "def a(x: int) -> int:\n    return x\n")
    assert release_gate(tmp_path, _snap(tmp_path)) == ()


# frob:ticket T-1009
class TestAuthoritativeVersion:
    """T-1009: `.frob-release.json` is the ONE version authority."""

    def test_reads_manifest_version(self, tmp_path):
        # frob:tests src/frob/release/__init__.py::authoritative_version
        _write(tmp_path, "def a(x: int) -> int:\n    return x\n")
        stamp(tmp_path, _snap(tmp_path), "3.4.5")
        assert authoritative_version(tmp_path).danger_ok == "3.4.5"

    def test_no_manifest_is_err(self, tmp_path):
        # frob:tests src/frob/release/__init__.py::authoritative_version
        result = authoritative_version(tmp_path)
        assert result.is_err
        assert result.danger_err == ReleaseError.NoManifest


# frob:ticket T-1009
class TestRewritePyprojectVersion:
    """T-1009: `pyproject.toml` is a DERIVED artifact -- `sync` rewrites
    it from the manifest's version, never the reverse."""

    def test_rewrites_when_different(self, tmp_path):
        # frob:tests src/frob/release/__init__.py::rewrite_pyproject_version
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "p"\nversion = "1.0.0"\n'
        )
        result = rewrite_pyproject_version(tmp_path, "2.0.0")
        assert result.danger_ok is True
        assert 'version = "2.0.0"' in (tmp_path / "pyproject.toml").read_text()

    def test_noop_when_already_matches(self, tmp_path):
        # frob:tests src/frob/release/__init__.py::rewrite_pyproject_version
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "p"\nversion = "2.0.0"\n'
        )
        result = rewrite_pyproject_version(tmp_path, "2.0.0")
        assert result.danger_ok is False

    def test_no_version_line_is_err(self, tmp_path):
        # frob:tests src/frob/release/__init__.py::rewrite_pyproject_version
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "p"\n')
        result = rewrite_pyproject_version(tmp_path, "2.0.0")
        assert result.is_err
        assert result.danger_err == ReleaseError.BadVersion

    def test_missing_file_is_err(self, tmp_path):
        # frob:tests src/frob/release/__init__.py::rewrite_pyproject_version
        result = rewrite_pyproject_version(tmp_path, "2.0.0")
        assert result.is_err


# frob:ticket T-1009
class TestChangelogSkeletonEntry:
    """T-1009: CHANGELOG.md is a DERIVED artifact -- `sync` adds a
    skeleton heading entry for the authoritative version if none exists."""

    def test_inserts_new_entry(self, tmp_path):
        # frob:tests src/frob/release/__init__.py::changelog_skeleton_entry
        (tmp_path / "CHANGELOG.md").write_text(
            "# Changelog\n\n## [1.0.0] - unreleased\n"
        )
        wrote = changelog_skeleton_entry(tmp_path, "2.0.0", note="T-0001: thing")
        assert wrote is True
        text = (tmp_path / "CHANGELOG.md").read_text()
        assert "## [2.0.0] - unreleased" in text
        assert "T-0001: thing" in text
        assert "## [1.0.0] - unreleased" in text  # old entry survives

    def test_existing_entry_is_noop(self, tmp_path):
        # frob:tests src/frob/release/__init__.py::changelog_skeleton_entry
        (tmp_path / "CHANGELOG.md").write_text(
            "# Changelog\n\n## [2.0.0] - unreleased\n\nalready here\n"
        )
        wrote = changelog_skeleton_entry(tmp_path, "2.0.0")
        assert wrote is False
        assert (tmp_path / "CHANGELOG.md").read_text().count("## [2.0.0]") == 1

    def test_missing_changelog_is_noop(self, tmp_path):
        # frob:tests src/frob/release/__init__.py::changelog_skeleton_entry
        assert changelog_skeleton_entry(tmp_path, "2.0.0") is False


# frob:ticket T-1009
# invariant spec: [INV-044](invariants/INV-044.md)
class TestReleaseGateCoherence:
    """T-1009: REL002 -- `.frob-release.json`'s version is authoritative;
    any derived artifact that disagrees is a hard ERROR, born from a
    clean baseline (DOC007 precedent, T-0986)."""

    def test_clean_repo_has_no_rel002(self, tmp_path):
        # frob:tests src/frob/gates/__init__.py::_rel002_coherence_violations
        from frob.gates import release_gate

        _write(tmp_path, "def a(x: int) -> int:\n    return x\n")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "p"\nversion = "1.0.0"\n', encoding="utf-8"
        )
        stamp(tmp_path, _snap(tmp_path), "1.0.0")
        (tmp_path / ".frob" / "cache.db").unlink()
        violations = release_gate(tmp_path, _snap(tmp_path))
        assert not any(v.rule == "REL002" for v in violations)

    def test_hand_edited_pyproject_fires_rel002(self, tmp_path):
        # frob:tests src/frob/gates/__init__.py::_rel002_coherence_violations
        from frob.gates import release_gate

        _write(tmp_path, "def a(x: int) -> int:\n    return x\n")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "p"\nversion = "1.0.0"\n', encoding="utf-8"
        )
        stamp(tmp_path, _snap(tmp_path), "1.0.0")
        (tmp_path / ".frob" / "cache.db").unlink()
        # Hand-edit pyproject.toml's version out from under the manifest --
        # the exact hazard REL002 exists to catch.
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "p"\nversion = "1.0.1"\n', encoding="utf-8"
        )
        violations = release_gate(tmp_path, _snap(tmp_path))
        rel002 = [v for v in violations if v.rule == "REL002"]
        assert len(rel002) == 1
        assert rel002[0].severity.name == "ERROR"
        assert "pyproject.toml" in rel002[0].message

    def test_hand_edited_uv_lock_fires_rel002(self, tmp_path):
        # frob:tests src/frob/gates/__init__.py::_rel002_coherence_violations
        from frob.gates import release_gate

        _write(tmp_path, "def a(x: int) -> int:\n    return x\n")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "p"\nversion = "1.0.0"\n', encoding="utf-8"
        )
        stamp(tmp_path, _snap(tmp_path), "1.0.0")
        (tmp_path / ".frob" / "cache.db").unlink()
        (tmp_path / "uv.lock").write_text(
            '[[package]]\nname = "p"\nversion = "0.9.0"\nsource = { editable = "." }\n',
            encoding="utf-8",
        )
        violations = release_gate(tmp_path, _snap(tmp_path))
        rel002 = [v for v in violations if v.rule == "REL002"]
        assert len(rel002) == 1
        assert "uv.lock" in rel002[0].message


# frob:ticket T-1359
class TestCrashSafeReleaseWrites:
    """T-1359: `stamp`/`rewrite_pyproject_version`/`changelog_skeleton_entry`/
    `set_manifest_version` all route their disk writes through
    `_atomic_write_release` (temp file + fsync + `os.replace`) instead of a
    bare `Path.write_text` -- a process killed mid-rename must leave the
    ORIGINAL file intact, never a torn/partial write (the T-1338 hazard
    class T-1348 already closed for `frob.gates._fix_engine`)."""

    def test_stamp_leaves_original_manifest_on_replace_failure(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ):
        # frob:tests \
        # tests/test_release.py::TestCrashSafeReleaseWrites.test_stamp_leaves_original_\
        # manifest_on_replace_failure
        _write(tmp_path, "def a(x: int) -> int:\n    return x\n")
        stamp(tmp_path, _snap(tmp_path), "1.0.0")
        original = manifest_path(tmp_path).read_text(encoding="utf-8")

        def _boom(src: str, dst: str) -> None:
            raise OSError("simulated crash mid-rename")

        monkeypatch.setattr(os, "replace", _boom)
        result = stamp(tmp_path, _snap(tmp_path), "2.0.0")

        assert result.is_err
        assert result.danger_err == ReleaseError.WriteFailed
        assert manifest_path(tmp_path).read_text(encoding="utf-8") == original
        leftovers = list(manifest_path(tmp_path).parent.glob(".*.tmp"))
        assert leftovers == [], f"a partial/temp file leaked: {leftovers}"

    def test_rewrite_pyproject_version_leaves_original_on_replace_failure(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ):
        # frob:tests \
        # tests/test_release.py::TestCrashSafeReleaseWrites.test_rewrite_pyproject_vers\
        # ion_leaves_original_on_replace_failure
        path = tmp_path / "pyproject.toml"
        path.write_text('[project]\nname = "p"\nversion = "1.0.0"\n', encoding="utf-8")

        def _boom(src: str, dst: str) -> None:
            raise OSError("simulated crash mid-rename")

        monkeypatch.setattr(os, "replace", _boom)
        result = rewrite_pyproject_version(tmp_path, "2.0.0")

        assert result.is_err
        assert result.danger_err == ReleaseError.WriteFailed
        assert 'version = "1.0.0"' in path.read_text(encoding="utf-8")
        leftovers = [p for p in tmp_path.iterdir() if p.name != "pyproject.toml"]
        assert leftovers == [], f"a partial/temp file leaked: {leftovers}"

    def test_changelog_skeleton_entry_leaves_original_on_replace_failure(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ):
        # frob:tests \
        # tests/test_release.py::TestCrashSafeReleaseWrites.test_changelog_skeleton_ent\
        # ry_leaves_original_on_replace_failure
        path = tmp_path / "CHANGELOG.md"
        original = "# Changelog\n\n## [1.0.0] - unreleased\n"
        path.write_text(original, encoding="utf-8")

        def _boom(src: str, dst: str) -> None:
            raise OSError("simulated crash mid-rename")

        monkeypatch.setattr(os, "replace", _boom)
        wrote = changelog_skeleton_entry(tmp_path, "2.0.0")

        assert wrote is False
        assert path.read_text(encoding="utf-8") == original
        leftovers = [p for p in tmp_path.iterdir() if p.name != "CHANGELOG.md"]
        assert leftovers == [], f"a partial/temp file leaked: {leftovers}"

    def test_set_manifest_version_leaves_original_on_replace_failure(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ):
        # frob:tests \
        # tests/test_release.py::TestCrashSafeReleaseWrites.test_set_manifest_version_l\
        # eaves_original_on_replace_failure
        _write(tmp_path, "def a(x: int) -> int:\n    return x\n")
        stamp(tmp_path, _snap(tmp_path), "1.0.0")
        original = manifest_path(tmp_path).read_text(encoding="utf-8")

        def _boom(src: str, dst: str) -> None:
            raise OSError("simulated crash mid-rename")

        monkeypatch.setattr(os, "replace", _boom)
        result = set_manifest_version(tmp_path, "2.0.0")

        assert result.is_err
        assert result.danger_err == ReleaseError.WriteFailed
        assert manifest_path(tmp_path).read_text(encoding="utf-8") == original
