"""T-4540: REL002 must not fire on a coherent PEP 440 dev version.

`frob.release.next_dev_version`'s per-land counter (T-4184) advances
`pyproject.toml`/`uv.lock` to `X.Y.(Z+1).devN` between release cuts, while
`.frob-release.json` still stamps the last final release (`X.Y.Z`). Before
this fix, `_rel002_coherence_violations` compared those two strings with a
flat `!=` and fired REL002 on every single land while `dev_version_bump`
is on (BUG002 repro below). A dev build whose base release is ahead of the
stamp is coherent by construction; a FINAL version that disagrees is still
a real desync and must still fire, unchanged.
"""

from __future__ import annotations

from pathlib import Path

from frob.graph import build_graph
from frob.release import stamp


def _snap(root: Path):
    """Build-and-return a fresh graph snapshot for `root` (shared setup)."""
    return build_graph(root, root / ".frob" / "cache.db").danger_ok


def _write_module(root: Path) -> None:
    """Write a minimal single-function module so the graph is non-empty."""
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "m.py").write_text(
        "def a(x: int) -> int:\n    return x\n", encoding="utf-8"
    )


def _write_pyproject(root: Path, version: str) -> None:
    """Write a minimal `pyproject.toml` stamped at `version`."""
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "p"\nversion = "{version}"\n', encoding="utf-8"
    )


def test_dev_version_ahead_of_stamp_does_not_fire_rel002(tmp_path):
    # frob:tests src/frob/gates/__init__.py::_rel002_coherence_violations
    """Proves `release_gate` reports zero REL002 findings when
    `dev_version_bump` is on and pyproject sits ahead of the stamp on a
    `.devN` suffix (T-4184's per-land dev bump shape) -- REL002 must not
    fire on every land in this configuration (see T-4540)."""
    from frob.gates import release_gate

    _write_module(tmp_path)
    _write_pyproject(tmp_path, "0.531.0")
    stamp(tmp_path, _snap(tmp_path), "0.531.0")
    (tmp_path / ".frob" / "cache.db").unlink()
    # Simulate T-4184's per-land dev bump: pyproject moves ahead of the
    # stamped final, dev_version_bump left on (default true).
    _write_pyproject(tmp_path, "0.531.1.dev3")
    violations = release_gate(tmp_path, _snap(tmp_path))
    assert not any(v.rule == "REL002" for v in violations)


def test_dev_version_ahead_of_stamp_in_lock_does_not_fire_rel002(tmp_path):
    # frob:tests src/frob/gates/__init__.py::_rel002_coherence_violations
    """Same coherence exemption applies to `uv.lock`'s recorded version,
    not only `pyproject.toml`'s."""
    from frob.gates import release_gate

    _write_module(tmp_path)
    _write_pyproject(tmp_path, "0.531.0")
    stamp(tmp_path, _snap(tmp_path), "0.531.0")
    (tmp_path / ".frob" / "cache.db").unlink()
    (tmp_path / "uv.lock").write_text(
        '[[package]]\nname = "p"\nversion = "0.531.1.dev3"\n'
        'source = { editable = "." }\n',
        encoding="utf-8",
    )
    violations = release_gate(tmp_path, _snap(tmp_path))
    assert not any(v.rule == "REL002" for v in violations)


def test_final_version_mismatch_still_fires_rel002(tmp_path):
    # frob:tests src/frob/gates/__init__.py::_rel002_coherence_violations
    """Criterion 2: a FINAL version (no `.devN` suffix) that disagrees
    with the stamp is a real desync and must still fire exactly as
    before -- the dev-suffix exemption must not swallow this case."""
    from frob.gates import release_gate

    _write_module(tmp_path)
    _write_pyproject(tmp_path, "1.0.0")
    stamp(tmp_path, _snap(tmp_path), "1.0.0")
    (tmp_path / ".frob" / "cache.db").unlink()
    # Hand-edited final version, no dev suffix -- still the exact hazard
    # REL002 exists to catch.
    _write_pyproject(tmp_path, "1.0.1")
    violations = release_gate(tmp_path, _snap(tmp_path))
    rel002 = [v for v in violations if v.rule == "REL002"]
    assert len(rel002) == 1
    assert "pyproject.toml" in rel002[0].message


def test_dev_version_behind_stamp_still_fires_rel002(tmp_path):
    # frob:tests src/frob/gates/__init__.py::_rel002_coherence_violations
    """A dev-suffixed version is only exempt when its base is genuinely
    AHEAD of the stamp -- a dev build whose base has fallen BEHIND (or
    equals) the stamped final is still a disagreement, not the T-4184
    per-land counter's coherent state."""
    from frob.gates import release_gate

    _write_module(tmp_path)
    _write_pyproject(tmp_path, "0.531.0")
    stamp(tmp_path, _snap(tmp_path), "0.531.0")
    (tmp_path / ".frob" / "cache.db").unlink()
    _write_pyproject(tmp_path, "0.530.0.dev3")
    violations = release_gate(tmp_path, _snap(tmp_path))
    rel002 = [v for v in violations if v.rule == "REL002"]
    assert len(rel002) == 1
