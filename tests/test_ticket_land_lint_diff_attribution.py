"""T-3132: `_assert_touched_files_lint_clean_pre_land` attributes `ruff`
findings to the DIFF, not the FILE -- ports T-3116's fix for the sibling
`ty` gate. A pre-existing violation whose surrounding code the diff
merely shifted must not refuse the land, but a genuinely new violation
still must, and a SECOND genuinely-new violation sharing `(file, code,
message)` identity with a pre-existing one must still refuse too (the
multiset-vs-set bug T-3116 hit during its own implementation).

Real git subprocesses and a real `ruff` invocation (matching
`tests/test_ticket_land_ty_diff_attribution.py`'s own established real-
tool idiom), not a mocked parser -- these tests prove the actual wiring
end to end, not just that some mocked call happened. Split into its own
module for the same reason as that file: `tests/test_ticket_work_and_
land_finish.py` leaks `FROB_WORKTREE` in-process (T-3123), which makes
node ids collected alongside it unbindable as evidence for a new
ticket's own gate.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


# frob:ticket T-3132
# frob:waive DUP001 reason="the run/git-init/commit-all trio is an established \
# real-git fixture idiom this test module family repeats \
# (tests/test_ticket_land_ty_diff_attribution.py, \
# tests/test_ticket_work_and_land_finish.py, tests/test_ticket_land.py, ... all carry \
# byte-identical copies already, none of them waived) -- extracting a shared conftest \
# helper is a real, independent cleanup outside T-3132's own scope, not something to \
# fold into this ticket's own land"
def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


# frob:ticket T-3132
# frob:waive DUP001 reason="see _run's identical DUP001 waiver immediately above -- \
# same established fixture idiom, same real cleanup-later disposition"
def _git_init(root: Path, *, branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


# frob:ticket T-3132
# frob:waive DUP001 reason="see _run's identical DUP001 waiver above -- same \
# established fixture idiom, same real cleanup-later disposition"
def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


# frob:ticket T-3132
_BAD_FN = "import os\n\n\ndef f() -> int:\n    return 1\n"
"""An unused `os` import -- a real, stable `ruff` F401 finding (error
severity per `_is_ruff_error_code`)."""


# frob:ticket T-3132
@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A `main` checkout with ONE committed `.py` file already carrying a
    real `ruff` F401 violation -- the parent-commit state every test in
    this module diffs against. Matches `tests/test_ticket_land_ty_diff_
    attribution.py::repo`'s shape."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    (main_repo / "src").mkdir()
    (main_repo / ".gitignore").write_text(".claude/\n.frob/\n")
    bad = main_repo / "src" / "bad_lint.py"
    bad.write_text(_BAD_FN)
    _commit_all(main_repo, "init with a pre-existing ruff violation")
    return main_repo


# frob:ticket T-3132
class TestRuffDiagnosticIdentity:
    """`_ruff_diagnostic_identity` (T-3132): `(relative_file, code,
    message)`, deliberately blind to `line`/`col`, and re-derived from
    `diag.file` relative to a caller-supplied base rather than passed
    through -- see the function's own docstring for why (`ruff`'s JSON
    output reports an ABSOLUTE `filename`, unlike `ty`)."""

    def test_ignores_line_and_col(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_land_lint_diff_attribution.py::TestRuffDiagnosticIdentity.test_ignores_line_and_col  # noqa: E501
        from frob.app.ticket_runner._land_cmd import _ruff_diagnostic_identity
        from frob.process.parsers.common import Diagnostic

        base = tmp_path
        near = Diagnostic(
            file=str(tmp_path / "src" / "bad_lint.py"),
            line=1,
            col=8,
            severity="error",
            code="F401",
            message="`os` imported but unused",
        )
        shifted = Diagnostic(
            file=str(tmp_path / "src" / "bad_lint.py"),
            line=9,
            col=8,
            severity="error",
            code="F401",
            message="`os` imported but unused",
        )
        assert _ruff_diagnostic_identity(
            base, near
        ) == _ruff_diagnostic_identity(base, shifted)

    def test_relative_to_base_not_absolute(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_land_lint_diff_attribution.py::TestRuffDiagnosticIdentity.test_relative_to_base_not_absolute  # noqa: E501
        # Two identical findings reported by two DIFFERENT spawning
        # directories (a live worktree and a detached baseline snapshot)
        # must still compare equal once re-based -- this is the whole
        # reason this function exists rather than reusing diag.file raw.
        from frob.app.ticket_runner._land_cmd import _ruff_diagnostic_identity
        from frob.process.parsers.common import Diagnostic

        live_base = tmp_path / "worktree"
        snapshot_base = tmp_path / "snapshot-xyz"
        live_diag = Diagnostic(
            file=str(live_base / "src" / "bad_lint.py"),
            line=1,
            col=8,
            severity="error",
            code="F401",
            message="`os` imported but unused",
        )
        snapshot_diag = Diagnostic(
            file=str(snapshot_base / "src" / "bad_lint.py"),
            line=1,
            col=8,
            severity="error",
            code="F401",
            message="`os` imported but unused",
        )
        assert _ruff_diagnostic_identity(
            live_base, live_diag
        ) == _ruff_diagnostic_identity(snapshot_base, snapshot_diag)


# frob:ticket T-3132
class TestAssertTouchedFilesLintCleanPreLand:
    """T-3132's own acceptance triple -- the touched-file `ruff` gate
    attributed to the DIFF, not the FILE."""

    def test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand.test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse  # noqa: E501
        # Must-stay-quiet fixture: the diff shifts the pre-existing
        # F401 a few lines down the file without touching the offending
        # import at all. Must NOT refuse.
        from frob.app.ticket_runner._land_cmd import (
            _assert_touched_files_lint_clean_pre_land,
        )

        bad = repo / "src" / "bad_lint.py"
        bad.write_text("\n\n\n\n\n" + _BAD_FN)

        _assert_touched_files_lint_clean_pre_land(
            repo, "T-3132", frozenset({"src/bad_lint.py"})
        )  # must not raise -- pre-existing, only relocated

    def test_genuinely_new_violation_still_refuses(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand.test_genuinely_new_violation_still_refuses  # noqa: E501
        # Must-fire fixture: a SECOND, genuinely new lint violation
        # (a different unused import) introduced alongside the
        # pre-existing one -- must still refuse.
        from frob.app.ticket_runner._land_cmd import (
            _assert_touched_files_lint_clean_pre_land,
        )

        bad = repo / "src" / "bad_lint.py"
        bad.write_text(_BAD_FN.replace("import os\n", "import os\nimport sys\n"))

        with pytest.raises(SystemExit) as exc_info:
            _assert_touched_files_lint_clean_pre_land(
                repo, "T-3132", frozenset({"src/bad_lint.py"})
            )
        assert exc_info.value.code == 1

    def test_second_new_violation_sharing_identity_with_pre_existing_one_still_refuses(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand.test_second_new_violation_sharing_identity_with_pre_existing_one_still_refuses  # noqa: E501
        # T-3116's own multiset-vs-set lesson, ported: a SECOND, textually
        # identical `os`-unused-import violation, in a different function
        # of the SAME file, shares its `(file, code, message)` identity
        # with the one pre-existing occurrence -- a plain set comparison
        # would let this hide behind the pre-existing one. Must refuse.
        from frob.app.ticket_runner._land_cmd import (
            _assert_touched_files_lint_clean_pre_land,
        )

        bad = repo / "src" / "bad_lint.py"
        # Two separate, textually-identical `import os` statements inside
        # two different function bodies -- each reported by ruff as its
        # own F401 finding sharing the same (file, code, message) shape.
        bad.write_text(
            "def f() -> int:\n"
            "    import os\n"
            "    return 1\n"
            "\n\n"
            "def g() -> int:\n"
            "    import os\n"
            "    return 2\n"
        )

        with pytest.raises(SystemExit) as exc_info:
            _assert_touched_files_lint_clean_pre_land(
                repo, "T-3132", frozenset({"src/bad_lint.py"})
            )
        assert exc_info.value.code == 1

    def test_baseline_unmeasurable_falls_back_to_file_scoped_refusal(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand.test_baseline_unmeasurable_falls_back_to_file_scoped_refusal  # noqa: E501
        # When the baseline snapshot cannot be built at all, this must
        # NOT be read as "everything is pre-existing" -- it degrades to
        # the pre-T-3132 file-scoped posture, so even the untouched,
        # unmodified pre-existing violation still refuses.
        import frob.app.ticket_runner._land_cmd as land_cmd

        monkeypatch.setattr(
            land_cmd, "_spawn_baseline_snapshot_worktree", lambda *_a, **_kw: None
        )

        with pytest.raises(SystemExit) as exc_info:
            land_cmd._assert_touched_files_lint_clean_pre_land(
                repo, "T-3132", frozenset({"src/bad_lint.py"})
            )
        assert exc_info.value.code == 1
