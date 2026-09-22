"""T-4459: a worktree test run through the ROOT checkout's interpreter
silently imports `frob` from the ROOT `src/` (the editable install's
`.pth` wins over an unset `PYTHONPATH`), measuring main's code instead of
the branch under test. `frob agent env`'s documented entry point
(`eval "$(frob agent env <worktree>)"`) is the fix: it must export
`PYTHONPATH=<worktree>/src` ahead of anything else, so a subsequent
`python -c "import frob"` resolves to the worktree's own checkout, not
another one -- see `frob.app.agent_runner._run_env`'s docstring and
`frob.doctor.ImportSourceStatus`/`_import_source_status` (the `frob
doctor` side of this same check) for the full contract."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

import pytest

from frob import doctor
from frob.app.agent_runner import run as agent_run
from frob.doctor import _import_source_status


# frob:ticket T-4459
def _git(*args: str, cwd: Path) -> None:
    """Run a `git` command in `cwd`, raising on any non-zero exit."""
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


# frob:ticket T-4459
def _init_repo(root: Path) -> None:
    """Minimal git repo fixture matching every other worktree-guard test's
    `_init_repo` shape (`tests/test_worktree_guard.py`), plus a `src/frob`
    package layout so the worktree this creates has genuine importable
    code, not just tracked files."""
    root.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "test@example.com", cwd=root)
    _git("config", "user.name", "Test", cwd=root)
    pkg = root / "src" / "frob"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("MARKER = 'main'\n")
    (root / "tickets.md").write_text("# Tickets\n\n")
    _git("add", "-A", cwd=root)
    _git("commit", "-q", "-m", "init", cwd=root)


# frob:ticket T-4459
class TestAgentEnvExportsWorktreePythonpath:
    """The documented entry point (`frob agent env`) must export a
    PYTHONPATH that makes `import frob` resolve to the WORKTREE's own
    `src/`, not whatever another checkout's editable install would
    otherwise win."""

    # frob:ticket T-4459
    def test_env_output_names_worktree_src_on_pythonpath(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """`frob agent env <worktree>`'s stdout contains an `export
        PYTHONPATH=...` line naming the worktree's own `src/` directory
        -- the exact line a dispatched agent's shell `eval`s."""
        main_repo = tmp_path / "main"
        _init_repo(main_repo)
        worktree = tmp_path / "wt"
        _git("worktree", "add", "-b", "feature", str(worktree), cwd=main_repo)

        agent_run(["env", str(worktree)])

        out = capsys.readouterr().out
        # The emitter renders every value through shlex.quote (a Windows
        # path with backslashes comes out single-quoted; a POSIX path is
        # printed bare), so assert the exact form it prints (T-4483).
        expected_src = shlex.quote(str((worktree / "src").resolve()))
        assert f"export PYTHONPATH={expected_src}" in out

    # frob:ticket T-4459
    def test_documented_entry_point_makes_worktree_code_importable(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """End-to-end T-4459 acceptance: exporting exactly the env `frob
        agent env <worktree>` prints, then running `python -c "import
        frob; print(frob.__file__)"` in a fresh subprocess (started with
        NO inherited PYTHONPATH of its own, the worst case), resolves to
        the WORKTREE's `src/frob/__init__.py` -- the exact measurement
        the ticket's MEASURED section describes doing by hand."""
        main_repo = tmp_path / "main"
        _init_repo(main_repo)
        worktree = tmp_path / "wt"
        _git("worktree", "add", "-b", "feature", str(worktree), cwd=main_repo)

        agent_run(["env", str(worktree)])
        out = capsys.readouterr().out
        exports: dict[str, str] = {}
        for line in out.splitlines():
            if not line.startswith("export "):
                continue
            key, _, value = line[len("export ") :].partition("=")
            exports[key] = value.strip("'\"")
        assert "PYTHONPATH" in exports

        proc = subprocess.run(
            ["python3", "-c", "import frob; print(frob.__file__)"],
            cwd=worktree,
            env={"PATH": "/usr/bin:/bin", "PYTHONPATH": exports["PYTHONPATH"]},
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        resolved = Path(proc.stdout.strip()).resolve()
        assert resolved == (worktree / "src" / "frob" / "__init__.py").resolve()


# frob:ticket T-4459
class TestImportSourceStatus:
    """T-4459: `frob.doctor._import_source_status` must report a clean,
    non-mismatched status when the currently-imported `frob` package's
    file IS the candidate root's own `src/frob/__init__.py`, and a loud
    mismatched status naming both paths when it is not -- the
    worktree-measures-main bug this whole ticket exists to catch. Kept in
    this file (not `tests/unit/test_doctor.py`) because it is bound to
    T-4459's own declared scope."""

    # frob:ticket T-4459
    # frob:tests src/frob/doctor.py::ImportSourceStatus
    def test_matching_worktree_reports_clean(self) -> None:
        """`resolved_root` whose own `src/frob/__init__.py` IS the
        currently-imported module resolves to `mismatched=False`."""
        status = _import_source_status(Path(doctor.__file__).parent.parent.parent)
        assert status.mismatched is False
        assert status.worktree_src == status.resolved_module_path

    # frob:ticket T-4459
    # frob:tests src/frob/doctor.py::ImportSourceStatus
    def test_mismatched_worktree_reports_loudly(self, tmp_path: Path) -> None:
        """A `resolved_root` with its OWN `src/frob/__init__.py`, distinct
        from the currently-imported module's file, resolves to
        `mismatched=True` naming both paths -- the exact T-4459 shape: a
        worktree test run silently importing another checkout's `frob`."""
        other_src = tmp_path / "src" / "frob"
        other_src.mkdir(parents=True)
        (other_src / "__init__.py").write_text("")
        status = _import_source_status(tmp_path)
        assert status.mismatched is True
        assert status.worktree_src == str((other_src / "__init__.py").resolve())
        assert status.resolved_module_path != status.worktree_src

    # frob:ticket T-4459
    # frob:tests src/frob/doctor.py::ImportSourceStatus
    def test_no_worktree_src_never_mismatches(self, tmp_path: Path) -> None:
        """A `resolved_root` with no `src/frob/__init__.py` of its own
        (e.g. an installed tool, no worktree layout) has nothing to
        mismatch against -- `worktree_src` is `None`, `mismatched` stays
        `False`."""
        status = _import_source_status(tmp_path)
        assert status.worktree_src is None
        assert status.mismatched is False
