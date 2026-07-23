"""frob.mutate: mutation testing (T-0011)."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

from frob.mutate import (
    MUTATION_RUN_ENV,
    MutateError,
    MutationResult,
    _Mutator,
    generate_mutants,
    run_mutations,
)


def test_generate_mutants_covers_operators():
    # frob:tests src/frob/mutate/__init__.py::generate_mutants
    src = "def f(a, b):\n    if a < b:\n        return a + b\n    return a and b\n"
    mutants = generate_mutants(src, "m.py").danger_ok
    descs = {m.mutant.description for m in mutants}
    assert any("compare" in d for d in descs)
    assert any("binop" in d for d in descs)
    assert any("boolop" in d for d in descs)
    # each mutant is valid parseable python that differs from the original
    assert all(m.source != src for m in mutants)


def test_generate_mutants_syntax_error_is_err():
    result = generate_mutants("def f(:\n", "m.py")
    assert result.is_err
    assert result.danger_err == MutateError.ParseFailed


def test_run_mutations_survivors_when_tests_weak(tmp_path):
    # frob:tests src/frob/mutate/__init__.py::run_mutations
    (tmp_path / "m.py").write_text(
        "def add(a, b):\n    return a + b\n", encoding="utf-8"
    )
    # a test that never asserts the result -> mutants survive
    (tmp_path / "t.py").write_text(
        "import m\ndef test_add():\n    m.add(1, 2)\n", encoding="utf-8"
    )
    result = run_mutations(
        tmp_path, Path("m.py"), ("python", "-m", "pytest", "-q", "t.py")
    )
    assert result.is_ok, result.err
    report = result.danger_ok
    assert report.total >= 1
    assert report.survivors  # the assert-free test kills nothing
    # the source is restored afterward
    assert (tmp_path / "m.py").read_text() == "def add(a, b):\n    return a + b\n"


def test_run_mutations_all_killed_by_strong_test(tmp_path):
    # frob:tests src/frob/mutate kind="integration"
    # run_mutations drives generate_mutants plus a real subprocess pytest
    # invocation end to end, scoring survivors against actual test output.
    (tmp_path / "m.py").write_text(
        "def add(a, b):\n    return a + b\n", encoding="utf-8"
    )
    (tmp_path / "t.py").write_text(
        "import m\n"
        "def test_add():\n"
        "    assert m.add(2, 3) == 5\n"
        "    assert m.add(0, 0) == 0\n",
        encoding="utf-8",
    )
    result = run_mutations(
        tmp_path, Path("m.py"), ("python", "-m", "pytest", "-q", "t.py")
    )
    report = result.danger_ok
    assert report.score == 1.0
    assert not report.survivors


# frob:ticket T-0755
def test_run_mutations_max_mutants_caps_points_explored(tmp_path):
    # frob:tests src/frob/mutate/__init__.py::run_mutations
    # 4 mutation points (2 compares, an add, an and); max_mutants=1 must
    # spawn the test command at most once, not four times.
    (tmp_path / "m.py").write_text(
        "def f(a, b):\n    if a < b and a > b:\n        return a + b\n    return 0\n",
        encoding="utf-8",
    )
    (tmp_path / "t.py").write_text(
        "import m\ndef test_f():\n    m.f(1, 2)\n", encoding="utf-8"
    )
    full = run_mutations(
        tmp_path, Path("m.py"), ("python", "-m", "pytest", "-q", "t.py")
    ).danger_ok
    assert full.total > 1  # sanity: more than one mutation point exists
    capped = run_mutations(
        tmp_path,
        Path("m.py"),
        ("python", "-m", "pytest", "-q", "t.py"),
        max_mutants=1,
    ).danger_ok
    assert capped.total == 1
    # the source is restored afterward, same as the uncapped run
    assert (tmp_path / "m.py").read_text().startswith("def f(a, b):")


# frob:ticket T-0755
def test_generate_mutants_line_ranges_filters_to_changed_lines():
    # frob:tests src/frob/mutate/__init__.py::generate_mutants
    # 4 mutable points total: line 2's compare, line 3's binop, and
    # (nested inside the compare) none else -- but line 5 has an
    # independent `and`. Restricting to line 5 only must drop every point
    # NOT on that line.
    src = (
        "def f(a, b):\n"
        "    if a < b:\n"
        "        return a + b\n"
        "    return 0\n"
        "    x = a and b\n"
    )
    unrestricted = generate_mutants(src, "m.py").danger_ok
    assert len(unrestricted) >= 3
    only_line5 = generate_mutants(src, "m.py", line_ranges=((5, 5),)).danger_ok
    assert len(only_line5) == 1
    assert "boolop" in only_line5[0].mutant.description
    assert only_line5[0].mutant.line == 5


def test_generate_mutants_line_ranges_no_match_is_empty():
    # frob:tests src/frob/mutate/__init__.py::generate_mutants
    src = "def f(a, b):\n    if a < b:\n        return a + b\n    return 0\n"
    result = generate_mutants(src, "m.py", line_ranges=((99, 99),)).danger_ok
    assert result == ()


def test_point_collector_indexing_matches_mutator():
    # frob:tests src/frob/mutate/__init__.py::_PointCollector
    # _PointCollector's whole contract is index parity: point index N in
    # its (index, lineno) list must be the exact point _Mutator(N) would
    # apply, across all four node kinds it mirrors. Verify against the
    # full generate_mutants enumeration on a source exercising each kind.
    import ast as ast_mod

    from frob.mutate import _PointCollector

    src = (
        "def f(a, b):\n"
        "    if a < b:\n"
        "        return a + b\n"
        "    x = a and b\n"
        "    return True\n"
    )
    mutants = generate_mutants(src, "m.py").danger_ok
    kinds = {m.mutant.description.split()[0] for m in mutants}
    assert {"compare", "binop", "boolop", "bool"} <= kinds
    collector = _PointCollector()
    collector.visit(ast_mod.parse(src))
    assert collector.points == [(i, m.mutant.line) for i, m in enumerate(mutants)]


# frob:ticket T-0755
def test_run_mutations_line_ranges_scopes_to_changed_lines(tmp_path):
    # frob:tests src/frob/mutate/__init__.py::run_mutations
    # T-0755 reviewer round 2 CRITICAL fix: a file-wide point selection
    # let an unrelated pre-existing line supply every mutant for a tiny
    # diff. Reproduce that shape directly: a "changed" 1-line function
    # (line 5) alongside unrelated pre-existing mutable code (line 2) --
    # scoping to line 5's span must mutate ONLY line 5.
    (tmp_path / "m.py").write_text(
        "def unrelated(a, b):\n"
        "    if a < b:\n"
        "        return a + b\n"
        "    return 0\n\n"
        "def changed(a, b):\n"
        "    return a and b\n",
        encoding="utf-8",
    )
    (tmp_path / "t.py").write_text(
        "import m\ndef test_changed():\n    m.changed(1, 2)\n", encoding="utf-8"
    )
    unrestricted = run_mutations(
        tmp_path, Path("m.py"), ("python", "-m", "pytest", "-q", "t.py")
    ).danger_ok
    assert unrestricted.total >= 2  # sees both unrelated.py's and changed's points
    scoped = run_mutations(
        tmp_path,
        Path("m.py"),
        ("python", "-m", "pytest", "-q", "t.py"),
        line_ranges=((6, 7),),
    ).danger_ok
    assert scoped.total == 1
    assert scoped.survivors[0].line == 7
    # the source is restored afterward
    assert (tmp_path / "m.py").read_text().startswith("def unrelated(a, b):")


# frob:ticket T-0755
def test_run_mutations_sets_mutation_run_sentinel_in_child_env(tmp_path):
    # frob:tests src/frob/mutate/__init__.py::run_mutations
    # Recursion guard: every spawned test process must see
    # MUTATION_RUN_ENV=1 so self-referential evidence (the TEST016
    # real-repo self-check) can refuse to re-enter the harness. The test
    # command here exits 0 (mutant SURVIVES) iff the sentinel is set, so
    # a harness that stopped stamping it would kill the mutant instead.
    (tmp_path / "m.py").write_text("def f(a, b):\n    return a + b\n", encoding="utf-8")
    probe = (
        "import os, sys\n"
        f"sys.exit(0 if os.environ.get({MUTATION_RUN_ENV!r}) == '1' else 1)\n"
    )
    (tmp_path / "probe.py").write_text(probe, encoding="utf-8")
    report = run_mutations(tmp_path, Path("m.py"), ("python", "probe.py")).danger_ok
    assert report.total >= 1
    assert report.killed == 0  # every mutant "survived": sentinel was seen


def test_run_mutations_missing_file(tmp_path):
    result = run_mutations(tmp_path, Path("nope.py"), ("true",))
    assert result.is_err
    assert result.danger_err == MutateError.NoSource


# frob:ticket T-0803
def test_run_mutations_kill_switch_refuses_without_spawning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # frob:tests src/frob/mutate/__init__.py::run_mutations
    # T-0803: FROB_DISABLE_EXEC=1 must make `run_mutations`'s per-mutant
    # test-suite spawn refuse (via `guarded_subprocess_run`) instead of
    # bypassing the T-0200/T-0778 exec guard -- proven with a spy on the
    # real `subprocess.run` so a spawn attempt would be observed. A
    # refused spawn is NOT a "killed" mutant: unlike a `TimeoutExpired`
    # hang (real, observed behavior under the mutant), a refusal ran
    # nothing, so scoring it as killed would fabricate a 100% mutation
    # score / zero survivors under the kill switch -- an env-var-gameable
    # rubber stamp. The whole run aborts with `Err(MutateError.
    # ExecDisabled)` instead (reviewer-mandated fix, matches
    # `_coverage_wait`/`_vm_runner`'s Err/raise semantics for the same
    # case).
    (tmp_path / "m.py").write_text(
        "def add(a, b):\n    return a + b\n", encoding="utf-8"
    )
    (tmp_path / "t.py").write_text(
        "import m\ndef test_add():\n    assert m.add(2, 3) == 5\n", encoding="utf-8"
    )
    monkeypatch.setenv("FROB_DISABLE_EXEC", "1")
    spawned = False
    real_run = subprocess.run

    def _spy(*args, **kwargs):  # noqa: ANN001, ANN202
        nonlocal spawned
        spawned = True
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _spy)
    result = run_mutations(
        tmp_path, Path("m.py"), ("python", "-m", "pytest", "-q", "t.py")
    )
    assert not spawned
    assert result.is_err
    assert result.danger_err == MutateError.ExecDisabled
    # the source is restored even though the run aborted
    assert (tmp_path / "m.py").read_text() == "def add(a, b):\n    return a + b\n"


def test_mutation_result_score():
    # frob:tests src/frob/mutate/__init__.py::MutationResult.score kind="unit"
    assert MutationResult(total=0, killed=0, survivors=()).score == 1.0
    assert MutationResult(total=4, killed=3, survivors=()).score == 0.75
    assert MutationResult(total=2, killed=0, survivors=()).score == 0.0


def _mutate_single(source: str, index: int) -> str:
    tree = ast.parse(source)
    mutator = _Mutator(index)
    mutator.visit(tree)
    assert mutator.applied is not None
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def test_mutator_visit_compare():
    # frob:tests src/frob/mutate/__init__.py::_Mutator.visit_Compare kind="unit"
    mutated = _mutate_single("a < b\n", 0)
    assert "a >= b" in mutated


def test_mutator_visit_bin_op():
    # frob:tests src/frob/mutate/__init__.py::_Mutator.visit_BinOp kind="unit"
    mutated = _mutate_single("a + b\n", 0)
    assert "a - b" in mutated


def test_mutator_visit_bool_op():
    # frob:tests src/frob/mutate/__init__.py::_Mutator.visit_BoolOp kind="unit"
    mutated = _mutate_single("a and b\n", 0)
    assert "a or b" in mutated


def test_mutator_visit_constant():
    # frob:tests src/frob/mutate/__init__.py::_Mutator.visit_Constant kind="unit"
    mutated = _mutate_single("x = True\n", 0)
    assert "False" in mutated
