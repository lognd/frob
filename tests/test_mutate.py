"""frob.mutate: mutation testing (T-0011)."""

from __future__ import annotations

from pathlib import Path

from frob.mutate import MutateError, generate_mutants, run_mutations


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
    (tmp_path / "m.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
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
    (tmp_path / "m.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
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


def test_run_mutations_missing_file(tmp_path):
    result = run_mutations(tmp_path, Path("nope.py"), ("true",))
    assert result.is_err
    assert result.danger_err == MutateError.NoSource
