"""LANDFMT001 gate tests (T-4298): `frob.gates._land_format.
land_format_gate` over a real git checkout -- the acceptance criterion
this ticket exists to satisfy is that `frob check --ticket <id>` (which
this gate plugs into) reports a finding for a diff-touched `.py` file
`ruff format` would rewrite, scoped to exactly this diff's own touched
files, never a whole-tree scan."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.gates._land_format import land_format_gate


# frob:waive DUP001 reason="same established real-git-fixture idiom \
# tests/unit/test_land_parity_gate.py's own _run/_git_init/_commit_all already carry \
# the identical DUP001 waiver for, citing the same real, independent shared-conftest \
# cleanup outside any one ticket's own scope"
def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _git_init(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A `main`-branch checkout with one committed baseline file --
    mirrors `tests/unit/test_land_parity_gate.py::repo`'s own fixture
    shape exactly (same reasoning: diffing `main` against itself, working
    tree included, is the cheapest fixture that gives `working_diff(root,
    "main")` a real touched-file set to compute)."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("x = 1\n")
    _commit_all(main_repo, "init")
    return main_repo


class _FakeProc:
    """Minimal `subprocess.CompletedProcess` stand-in -- same fake shape
    `tests/unit/test_check.py`'s own `TestRunRuffRealPaths` family uses to
    avoid a real `uv run --project <tmp_path>` spawn against a bare git
    fixture with no `pyproject.toml`/lockfile of its own."""

    def __init__(self, stdout: str, returncode: int) -> None:
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


def test_diff_touched_unformatted_file_fires(repo: Path, monkeypatch) -> None:
    """A diff-touched `.py` file `ruff format --check` reports as
    needing a rewrite fires LANDFMT001 -- the T-4298 acceptance
    criterion this gate exists to satisfy. `guarded_subprocess_run` is
    faked (same idiom as `tests/unit/test_check.py::
    TestRunRuffRealPaths`) so this test does not depend on a real `uv
    run --project` spawn resolving inside the bare git fixture."""
    from typani import Ok

    import frob.gates._land_format as land_format_mod

    (repo / "src" / "feature.py").write_text("x=1\n")

    def _fake_run(cmd, **kw):  # noqa: ANN001
        return Ok(_FakeProc("Would reformat src/feature.py\n", 1))

    monkeypatch.setattr(land_format_mod, "guarded_subprocess_run", _fake_run)
    violations = land_format_gate(repo)
    rules = {v.rule for v in violations}
    assert "LANDFMT001" in rules
    assert any(v.file == "src/feature.py" for v in violations)


def test_already_formatted_touched_file_is_quiet(repo: Path, monkeypatch) -> None:
    """`ruff format --check` reporting nothing to rewrite (exit 0) is
    quiet -- LANDFMT001 must not fire on a file it has nothing to say
    about."""
    from typani import Ok

    import frob.gates._land_format as land_format_mod

    (repo / "src" / "feature.py").write_text("x = 1\n")

    def _fake_run(cmd, **kw):  # noqa: ANN001
        return Ok(_FakeProc("", 0))

    monkeypatch.setattr(land_format_mod, "guarded_subprocess_run", _fake_run)
    violations = land_format_gate(repo)
    assert violations == ()


def test_no_diff_is_quiet(repo: Path) -> None:
    """No working-tree diff against `main` at all -- `()`, matching
    `land_parity_doc_test_gate`'s/`land_parity_long_function_gate`'s own
    fail-open posture for the identical case. No `ruff` invocation is
    even reachable here (nothing patched), since `_land_format_touched_
    py_files` returns `None` before any subprocess call would happen."""
    violations = land_format_gate(repo)
    assert violations == ()
