"""T-3116: `_assert_touched_files_type_check_pre_land` attributes `ty`
findings to the DIFF, not the FILE -- a pre-existing finding whose
surrounding code the diff merely shifted must not refuse the land, but a
genuinely new finding still must. Split into its OWN module rather than
appended to `tests/test_ticket_work_and_land_finish.py` (T-1907's own
home): that module's `TestLandParityFindings` and friends currently LEAK
`FROB_WORKTREE` in-process (T-3123), which makes node ids collected
alongside them unbindable as evidence for a NEW ticket's own ARCH gate.

Real git subprocesses and a real `ty` invocation (matching this repo's
established fixture idiom in `tests/test_ticket_work_and_land_finish.py`
and `tests/test_ticket_land.py`), not a mocked parser -- these tests prove
the actual wiring end to end, not just that some mocked call happened.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


# frob:ticket T-3116
# frob:waive DUP001 reason="the run/git-init/commit-all trio is an established \
# real-git fixture idiom this test module family repeats \
# (tests/test_ticket_work_and_land_finish.py, tests/test_ticket_land.py, \
# tests/test_ticket_leases.py, ... all carry byte-identical copies already, none of \
# them waived) -- extracting a shared conftest helper is a real, independent cleanup \
# outside T-3116's own scope, not something to fold into this ticket's own land"
def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


# frob:ticket T-3116
# frob:waive DUP001 reason="see _run's identical DUP001 waiver immediately above -- \
# same established fixture idiom, same real cleanup-later disposition"
def _git_init(root: Path, *, branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


# frob:ticket T-3116
# frob:waive DUP001 reason="see _run's identical DUP001 waiver above -- same \
# established fixture idiom, same real cleanup-later disposition"
def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


# frob:ticket T-3116
_BAD_FN = 'def f(x: int) -> int:\n    return "not an int"\n'


# frob:ticket T-3116
@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A `main` checkout with an initialized ledger-free repo and ONE
    committed `.py` file already carrying a real `ty` error -- the
    parent-commit state every test in this module diffs against. Matches
    `tests/test_ticket_work_and_land_finish.py::repo`'s shape (real git,
    `.gitignore` for `.claude/`/`.frob/`) minus the ticket-ledger init
    this module's tests never touch."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    (main_repo / "src").mkdir()
    (main_repo / ".gitignore").write_text(".claude/\n.frob/\n")
    bad = main_repo / "src" / "bad_types.py"
    bad.write_text(_BAD_FN)
    _commit_all(main_repo, "init with a pre-existing ty error")
    return main_repo


# frob:ticket T-3116
class TestTyDiagnosticIdentity:
    """`_ty_diagnostic_identity` (T-3116): `(file, code, message)`,
    deliberately blind to `line`/`col`."""

    def test_ignores_line_and_col(self) -> None:
        # frob:tests tests/test_ticket_land_ty_diff_attribution.py::TestTyDiagnosticIdentity.test_ignores_line_and_col  # noqa: E501
        from frob.app.ticket_runner._land_cmd import _ty_diagnostic_identity
        from frob.process.parsers.common import Diagnostic

        near = Diagnostic(
            file="src/bad_types.py",
            line=2,
            col=12,
            severity="error",
            code="invalid-return-type",
            message="expected `int`, found `str`",
        )
        shifted = Diagnostic(
            file="src/bad_types.py",
            line=9,
            col=12,
            severity="error",
            code="invalid-return-type",
            message="expected `int`, found `str`",
        )
        assert _ty_diagnostic_identity(near.file, near) == _ty_diagnostic_identity(
            shifted.file, shifted
        )


# frob:ticket T-3116
class TestAssertTouchedFilesTypeCheckPreLand:
    """T-3116's own acceptance pair, plus the unmeasurable-baseline
    fallback -- the touched-file `ty` gate attributed to the DIFF."""

    def test_pre_existing_finding_that_merely_shifted_lines_does_not_refuse(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land_ty_diff_attribution.py::TestAssertTouchedFilesTypeCheckPreLand.test_pre_existing_finding_that_merely_shifted_lines_does_not_refuse  # noqa: E501
        # The exact measured incident: the diff shifts the pre-existing
        # error a few lines down the file (a handful of blank lines
        # inserted above it) without touching the offending expression
        # at all. Must NOT refuse.
        from frob.app.ticket_runner._land_cmd import (
            _assert_touched_files_type_check_pre_land,
        )

        bad = repo / "src" / "bad_types.py"
        bad.write_text("\n\n\n\n\n" + _BAD_FN)

        _assert_touched_files_type_check_pre_land(
            repo, "T-3116", frozenset({"src/bad_types.py"})
        )  # must not raise -- pre-existing, only relocated

    def test_genuinely_new_finding_still_refuses(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land_ty_diff_attribution.py::TestAssertTouchedFilesTypeCheckPreLand.test_genuinely_new_finding_still_refuses  # noqa: E501
        # A SECOND, genuinely new type error introduced alongside the
        # pre-existing one -- must still refuse (T-3116 must not turn
        # this gate off for touched files carrying any pre-existing
        # finding, only exempt the pre-existing finding itself).
        from frob.app.ticket_runner._land_cmd import (
            _assert_touched_files_type_check_pre_land,
        )

        bad = repo / "src" / "bad_types.py"
        bad.write_text(
            _BAD_FN + '\n\ndef g(y: int) -> int:\n    return "also not an int"\n'
        )

        with pytest.raises(SystemExit) as exc_info:
            _assert_touched_files_type_check_pre_land(
                repo, "T-3116", frozenset({"src/bad_types.py"})
            )
        assert exc_info.value.code == 1

    def test_baseline_unmeasurable_falls_back_to_file_scoped_refusal(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land_ty_diff_attribution.py::TestAssertTouchedFilesTypeCheckPreLand.test_baseline_unmeasurable_falls_back_to_file_scoped_refusal  # noqa: E501
        # When the baseline snapshot cannot be built at all, this must
        # NOT be read as "everything is pre-existing" -- it degrades to
        # the pre-T-3116 file-scoped posture, so even the untouched,
        # unmodified pre-existing finding still refuses.
        import frob.app.ticket_runner._land_cmd as land_cmd

        monkeypatch.setattr(
            land_cmd, "_spawn_baseline_snapshot_worktree", lambda *_a, **_kw: None
        )

        with pytest.raises(SystemExit) as exc_info:
            land_cmd._assert_touched_files_type_check_pre_land(
                repo, "T-3116", frozenset({"src/bad_types.py"})
            )
        assert exc_info.value.code == 1


# frob:ticket T-4275
class TestTyCheckFilesResolveRoot:
    """T-4275: `_ty_check_files`'s `resolve_root` split (porting T-4257's
    identical fix for `_ruff_check_files`) -- a caller scanning a
    disposable, `.venv`-less snapshot must be able to resolve `ty` from
    the REAL owning worktree instead of falling back to bare-PATH
    resolution outside any project, and a genuine spawn failure must
    come back as `None` (unmeasurable), never a fabricated clean
    `ToolResult`."""

    def test_resolve_root_finds_ty_when_cwd_has_no_pyproject(
        self, repo: Path, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_land_ty_diff_attribution.py::TestTyCheckFilesResolveRoot.te\
        # st_resolve_root_finds_ty_when_cwd_has_no_pyproject
        # A bare-PATH `uv run --project <no-pyproject-dir>` cannot resolve
        # `ty` (T-4257's measured Windows gap, its `ruff` sibling); before
        # T-4275 this call had no `resolve_root` parameter at all, so a
        # baseline scan of a venv-less snapshot always ran through this
        # broken path. `snapshot` here stands in for that snapshot: no
        # pyproject.toml, no .venv, only the one file to check.
        from frob.app.ticket_runner._land_cmd import _ty_check_files

        snapshot = tmp_path / "snapshot"
        snapshot.mkdir()
        bad = snapshot / "bad_types.py"
        bad.write_text('def f(x: int) -> int:\n    return "not an int"\n')

        result = _ty_check_files(snapshot, ["bad_types.py"], resolve_root=repo)

        assert result is not None
        assert any(d.severity == "error" for d in result.diagnostics)

    def test_spawn_failure_reports_none_not_a_fabricated_clean_result(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_ticket_land_ty_diff_attribution.py::TestTyCheckFilesResolveRoot.te\
        # st_spawn_failure_reports_none_not_a_fabricated_clean_result
        # T-4275: before this fix, feeding empty stdout/stderr to
        # `parse_ty` silently came back as a CLEAN `ToolResult` (its
        # line-scanner finds zero diagnostic lines in zero lines of
        # input) -- indistinguishable from a real "no errors" run. A
        # completed process with genuinely empty output on both streams
        # can only mean the spawn never actually invoked `ty` at all;
        # `_ty_check_files` must report that as `None` (unmeasurable),
        # not as 0 diagnostics.
        import subprocess as subprocess_module

        from frob.app.ticket_runner._land_cmd import _ty_check_files

        def _fake_run(
            cmd: list[str], **kwargs: object
        ) -> subprocess_module.CompletedProcess[str]:
            return subprocess_module.CompletedProcess(
                args=cmd,
                returncode=2,
                stdout="",
                stderr="",
            )

        monkeypatch.setattr(subprocess_module, "run", _fake_run)

        good = repo / "src" / "good_types.py"
        good.write_text("def f(x: int) -> int:\n    return x + 1\n")

        result = _ty_check_files(repo, ["src/good_types.py"])

        assert result is None
