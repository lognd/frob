"""frob.release: mechanical semver from the public-API graph (T-0003)."""

from __future__ import annotations

from pathlib import Path

from frob.graph import build_graph
from frob.release import (
    BumpClass,
    diff_class,
    load_manifest,
    required_version,
    satisfies,
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
    assert diff_class(load_manifest(tmp_path).danger_ok, _snap(tmp_path)) == BumpClass.NONE


def test_new_public_symbol_is_minor(tmp_path):
    # frob:tests src/frob/release/__init__.py::diff_class
    _write(tmp_path, "def a(x: int) -> int:\n    return x\n")
    stamp(tmp_path, _snap(tmp_path), "1.0.0")
    manifest = load_manifest(tmp_path).danger_ok
    _write(tmp_path, "def a(x: int) -> int:\n    return x\ndef b() -> int:\n    return 0\n")
    (tmp_path / ".frob" / "cache.db").unlink()
    assert diff_class(manifest, _snap(tmp_path)) == BumpClass.MINOR


def test_changed_signature_is_major(tmp_path):
    _write(tmp_path, "def a(x: int) -> int:\n    return x\n")
    stamp(tmp_path, _snap(tmp_path), "1.0.0")
    manifest = load_manifest(tmp_path).danger_ok
    _write(tmp_path, "def a(x: int, y: int) -> int:\n    return x + y\n")
    (tmp_path / ".frob" / "cache.db").unlink()
    assert diff_class(manifest, _snap(tmp_path)) == BumpClass.MAJOR


def test_required_version_and_satisfies():
    assert required_version("1.2.3", BumpClass.MAJOR).danger_ok == "2.0.0"
    assert required_version("1.2.3", BumpClass.MINOR).danger_ok == "1.3.0"
    assert required_version("1.2.3", BumpClass.PATCH).danger_ok == "1.2.4"
    assert satisfies("2.0.0", "2.0.0")
    assert not satisfies("1.9.9", "2.0.0")


def test_release_gate_flags_missing_bump(tmp_path):
    # frob:tests src/frob/gates/__init__.py::release_gate
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
