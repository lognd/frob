"""Unit tests for frob.dup._pipeline.probe_smt_equivalence (docs/dup.md's R7).

`z3-solver` is optional (`frob[smt]`) and not installed in every dev/CI
environment, so this file always exercises the honest degrade path
(`Err(SmtUnavailable)`) and additionally runs the real-proof/counterexample
paths whenever z3 happens to be importable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.dup._models import DupError
from frob.dup._pipeline import probe_smt_equivalence
from frob.graph._models import GraphSnapshot

try:
    import z3  # noqa: F401  # ty: ignore[unresolved-import]

    HAS_Z3 = True
except ImportError:
    HAS_Z3 = False


def _empty_snapshot() -> GraphSnapshot:
    return GraphSnapshot(root=".", symbols={}, edges=())


# frob:tests src/frob/dup/_pipeline.py::probe_smt_equivalence kind="unit"
def test_degrades_to_smt_unavailable_without_z3(monkeypatch: pytest.MonkeyPatch):
    if HAS_Z3:
        pytest.skip("z3-solver is installed; this exercises the absent-dep path")
    result = probe_smt_equivalence("a", "b", _empty_snapshot())
    assert result.is_err
    assert result.err == DupError.SmtUnavailable


@pytest.mark.skipif(not HAS_Z3, reason="z3-solver not installed")
def test_proves_equivalent_bounded_functions(tmp_path: Path):
    from frob.gitio import Diff  # noqa: F401  (import kept local to this branch)
    from frob.graph import build_graph

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "m.py").write_text(
        "def double_a(x: int) -> int:\n    return x + x\n\n"
        "def double_b(x: int) -> int:\n    return x * 2\n",
        encoding="utf-8",
    )
    snapshot = build_graph(tmp_path, tmp_path / "cache").danger_ok
    a = next(r for r in snapshot.symbols if "double_a" in r)
    b = next(r for r in snapshot.symbols if "double_b" in r)
    result = probe_smt_equivalence(a, b, snapshot)
    assert result.is_ok, result.err
    assert result.danger_ok.equivalent is True


@pytest.mark.skipif(not HAS_Z3, reason="z3-solver not installed")
def test_finds_counterexample_for_non_equivalent_functions(tmp_path: Path):
    from frob.graph import build_graph

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "m.py").write_text(
        "def inc_a(x: int) -> int:\n    return x + 1\n\n"
        "def inc_b(x: int) -> int:\n    return x + 2\n",
        encoding="utf-8",
    )
    snapshot = build_graph(tmp_path, tmp_path / "cache").danger_ok
    a = next(r for r in snapshot.symbols if "inc_a" in r)
    b = next(r for r in snapshot.symbols if "inc_b" in r)
    result = probe_smt_equivalence(a, b, snapshot)
    assert result.is_ok, result.err
    assert result.danger_ok.equivalent is False
    assert result.danger_ok.counterexample
