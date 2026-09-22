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
import sys
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

    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_assert_touched_files_lint_clean_pre_land  # noqa: E501
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
        assert _ruff_diagnostic_identity(base, near) == _ruff_diagnostic_identity(
            base, shifted
        )

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

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="T-4445: backslash/drive-letter path shape is win32-only "
        "-- os.path.relpath/normcase are platform-native, so exercising "
        "Windows-style path text through posixpath on linux/macOS would "
        "test posixpath's rules, not the win32 behavior this guards",
    )
    def test_backslash_and_drive_letter_case_do_not_break_identity(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_ticket_land_lint_diff_attribution.py::TestRuffDiagnosticIdentity.test_backslash_and_drive_letter_case_do_not_break_identity  # noqa: E501
        # T-4445: a Windows CI runner and a Windows dev mirror can each
        # report the SAME relative file with different backslash/forward-
        # slash or drive-letter-case text (`os.path.relpath` is purely
        # lexical, so it never normalizes either). Both spellings of the
        # same file must still compare equal.
        from frob.app.ticket_runner._land_cmd import _ruff_diagnostic_identity
        from frob.process.parsers.common import Diagnostic

        base = Path("C:\\work\\worktree")
        lower_backslash = Diagnostic(
            file="c:\\work\\worktree\\src\\bad_lint.py",
            line=1,
            col=8,
            severity="error",
            code="F401",
            message="`os` imported but unused",
        )
        upper_forwardslash = Diagnostic(
            file="C:/work/worktree/src/bad_lint.py",
            line=9,
            col=8,
            severity="error",
            code="F401",
            message="`os` imported but unused",
        )
        assert _ruff_diagnostic_identity(
            base, lower_backslash
        ) == _ruff_diagnostic_identity(base, upper_forwardslash)


# frob:ticket T-3132
class TestAssertTouchedFilesLintCleanPreLand:
    """T-3132's own acceptance triple -- the touched-file `ruff` gate
    attributed to the DIFF, not the FILE."""

    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_assert_touched_files_lint_clean_pre_land  # noqa: E501
    def test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse(
        self,
        repo: Path,
        capsys: pytest.CaptureFixture[str],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand.test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse  # noqa: E501
        # Must-stay-quiet fixture: the diff shifts the pre-existing
        # F401 a few lines down the file without touching the offending
        # import at all. Must NOT refuse.
        #
        # T-4457: CI run 34739935923's Windows leg refused here with only
        # a bare `SystemExit: 1` in the trimmed traceback -- the actual
        # mismatching identity pair was captured by `_refuse_pre_land_
        # lint`'s stderr message and `_ruff_new_violations`' own
        # `_log.warning`, neither of which the runner log printed. Wrap
        # the call so a REGRESSION here surfaces that detail directly in
        # the failure's own message instead of an opaque `SystemExit`.
        import logging

        from frob.app.ticket_runner._land_cmd import (
            _assert_touched_files_lint_clean_pre_land,
        )

        bad = repo / "src" / "bad_lint.py"
        bad.write_text("\n\n\n\n\n" + _BAD_FN)

        with caplog.at_level(logging.WARNING):
            try:
                _assert_touched_files_lint_clean_pre_land(
                    repo, "T-3132", frozenset({"src/bad_lint.py"})
                )
            except SystemExit as exc:
                captured = capsys.readouterr()
                raise AssertionError(
                    "expected no refusal (pre-existing violation merely "
                    f"shifted lines) but got SystemExit({exc.code}); "
                    f"stdout={captured.out!r} stderr={captured.err!r} "
                    f"log={caplog.text!r}"
                ) from exc

    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_assert_touched_files_lint_clean_pre_land  # noqa: E501
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

    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_assert_touched_files_lint_clean_pre_land  # noqa: E501
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

    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_assert_touched_files_lint_clean_pre_land  # noqa: E501
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


# frob:ticket T-4457
class TestRelativizeDiagPath:
    """`_relativize_diag_path` (T-4457): the pure, mock-free path-shaping
    half of `_ruff_diagnostic_identity`, driven through an injectable
    `path_mod` so its win32 drive-letter behavior is exercisable on any
    host -- `ntpath` implements the real win32 `splitdrive`/`relpath`/
    `normcase` rules regardless of which OS this test itself runs on."""

    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_relativize_diag_path
    def test_same_drive_relativizes_normally(self) -> None:
        # frob:tests \
        # tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath.test_\
        # same_drive_relativizes_normally
        import ntpath

        from frob.app.ticket_runner._land_cmd import _relativize_diag_path

        assert _relativize_diag_path(
            "C:\\work\\worktree\\src\\bad_lint.py",
            "C:\\work\\worktree",
            path_mod=ntpath,
        ) == ntpath.normcase("src\\bad_lint.py")

    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_relativize_diag_path
    def test_cross_drive_diag_and_base_do_not_crash(self) -> None:
        # frob:tests \
        # tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath.test_\
        # cross_drive_diag_and_base_do_not_crash
        # Defense in depth: `ntpath.relpath` RAISES ValueError when its
        # two arguments name different drives. Nothing in the current
        # call sites ever pairs a diag_file with a same-tree-foreign
        # base (each pass's diagnostics are always relative to the SAME
        # directory that pass spawned `ruff` in -- see `_ruff_diagnostic_
        # identity`'s own docstring), but a caller that ever did must
        # degrade to a stable fallback rather than crash the land.
        import ntpath

        from frob.app.ticket_runner._land_cmd import _relativize_diag_path

        identity = _relativize_diag_path(
            "D:\\a\\frob\\frob\\src\\bad_lint.py",
            "C:\\Users\\runneradmin\\AppData\\Local\\Temp\\frob-land-baseline-xyz",
            path_mod=ntpath,
        )
        assert identity == ntpath.normcase(
            ntpath.abspath("D:\\a\\frob\\frob\\src\\bad_lint.py")
        )

    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_relativize_diag_path
    def test_live_and_baseline_pass_agree_across_differently_drived_trees(
        self,
    ) -> None:
        # frob:tests \
        # tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath.test_\
        # live_and_baseline_pass_agree_across_differently_drived_trees
        # T-4457's own acceptance shape: a GitHub-hosted Windows runner's
        # checkout (D:\a\frob\frob, the live pass's tree) and its
        # baseline snapshot (spawned under the process temp dir,
        # C:\Users\runneradmin\...\Temp, the baseline pass's tree) sit on
        # DIFFERENT drives from EACH OTHER -- but within each individual
        # pass, `diag_file` and `base` are always drawn from that SAME
        # pass's own tree (ruff reports paths under whatever directory it
        # was spawned in), so `relpath` never actually crosses drives
        # WITHIN one call. The byte-identical file at the same relative
        # position in both trees must still produce the SAME identity.
        import ntpath

        from frob.app.ticket_runner._land_cmd import _relativize_diag_path

        live_identity = _relativize_diag_path(
            "D:\\a\\frob\\frob\\src\\bad_lint.py",
            "D:\\a\\frob\\frob",
            path_mod=ntpath,
        )
        baseline_identity = _relativize_diag_path(
            "C:\\Users\\runneradmin\\AppData\\Local\\Temp\\frob-land-baseline-xyz"
            "\\src\\bad_lint.py",
            "C:\\Users\\runneradmin\\AppData\\Local\\Temp\\frob-land-baseline-xyz",
            path_mod=ntpath,
        )
        assert live_identity == baseline_identity == "src\\bad_lint.py"

    # frob:ticket T-4461
    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_relativize_diag_path
    def test_ntpath_absolute_snapshot_rooted_diag_file_matches_live_identity(
        self,
    ) -> None:
        # frob:tests \
        # tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath.test_\
        # ntpath_absolute_snapshot_rooted_diag_file_matches_live_identity
        # T-4461's own acceptance shape, ported from T-4457's sibling test
        # above: a baseline pass's `diag.file` reported as an ABSOLUTE
        # path under the snapshot root, relativized against that SAME
        # snapshot root as `base` -- exactly `_ruff_baseline_diagnostic_
        # identities`' own call shape (`_ruff_diagnostic_identity(
        # snapshot, d)`) -- must land on the identical identity a live
        # pass produces for the same relative file under a DIFFERENT
        # root.
        import ntpath

        from frob.app.ticket_runner._land_cmd import _relativize_diag_path

        live_identity = _relativize_diag_path(
            "D:\\a\\frob\\frob\\src\\bad_lint.py",
            "D:\\a\\frob\\frob",
            path_mod=ntpath,
        )
        baseline_identity = _relativize_diag_path(
            "C:\\Users\\RUNNER~1\\AppData\\Local\\Temp\\frob-land-baseline-5d1uymtm"
            "\\src\\bad_lint.py",
            "C:\\Users\\RUNNER~1\\AppData\\Local\\Temp\\frob-land-baseline-5d1uymtm",
            path_mod=ntpath,
        )
        assert live_identity == baseline_identity == "src\\bad_lint.py"

    # frob:ticket T-4461
    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_relativize_diag_path
    def test_posix_absolute_tmp_snapshot_path_matches_live_identity(self) -> None:
        # frob:tests \
        # tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath.test_\
        # posix_absolute_tmp_snapshot_path_matches_live_identity
        # The POSIX-side analogue of the ntpath test above: an absolute
        # `/tmp`-rooted snapshot path relativized against that same
        # snapshot root must agree with a live pass's identity for the
        # same relative file under a different root.
        import posixpath

        from frob.app.ticket_runner._land_cmd import _relativize_diag_path

        live_identity = _relativize_diag_path(
            "/home/runner/work/frob/frob/src/bad_lint.py",
            "/home/runner/work/frob/frob",
            path_mod=posixpath,
        )
        baseline_identity = _relativize_diag_path(
            "/tmp/frob-land-baseline-5d1uymtm/src/bad_lint.py",
            "/tmp/frob-land-baseline-5d1uymtm",
            path_mod=posixpath,
        )
        assert live_identity == baseline_identity == "src/bad_lint.py"

    # frob:ticket T-4461
    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_relativize_diag_path
    def test_symlinked_snapshot_diag_file_unresolved_matches_realpath_base(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath.test_\
        # symlinked_snapshot_diag_file_unresolved_matches_realpath_base
        # The genuine, filesystem-level REPRO of T-4461's bug class on
        # POSIX (no 8.3 short names exist here, but the same shape --
        # `diag_file` and `base` naming the identical file through two
        # DIFFERENT-depth resolutions -- reproduces via a real symlink,
        # matching T-3497's own macOS /tmp -> /private/tmp precedent).
        # `diag_file` is given UNRESOLVED, through the symlink; `base` is
        # given already fully resolved. Before T-4461's fix (only `base`
        # went through any realpath-equivalent step, never `diag_file`),
        # `os.path.relpath` would compute a WRONG, climbing-out relative
        # path here because the two strings do not share a lexical
        # prefix even though they name the same file -- run this test
        # against the pre-fix code (single-sided `base.resolve()`, raw
        # `diag_file`) and it fails, which is exactly the check-repro
        # evidence this ticket requires.
        import os

        from frob.app.ticket_runner._land_cmd import _relativize_diag_path

        real_dir = tmp_path / "real-target"
        (real_dir / "src").mkdir(parents=True)
        (real_dir / "src" / "bad_lint.py").write_text("import os\n")
        link_dir = tmp_path / "symlinked-snapshot"
        link_dir.symlink_to(real_dir)

        diag_file = str(link_dir / "src" / "bad_lint.py")
        base = str(real_dir)

        identity = _relativize_diag_path(diag_file, base)

        expected = os.path.normcase(os.path.join("src", "bad_lint.py"))
        assert identity == expected
        assert not identity.startswith("..")
