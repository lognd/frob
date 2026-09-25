"""T-5403: `frob.tickets._land._dry_run_squash_preview_pre_commit_checks` --
a `--dry-run` land used to report READY the instant its ordinary merge and
post-merge re-verifications passed, never building the SQUASH preview a
real land commits from, so the T-3324 self-conformance sweep and the
DOC006/SELFAUDIT001 findings a real land's `_run_pre_commit_checks` runs
against that preview were only ever discovered at the real land (observed
twice: T-5302, T-5360). Exercises the new function directly against a
scratch git repo (`root` + a separate `worktree` checkout of a ticket
branch), mocking `frob.gates._sys.*_findings_touching` at the same seam
`TestSelfauditFindingsInTouchedFiles` (tests/test_ticket_work_and_land_
finish.py) already established for the real-land check this dry-run path
now shares."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.gates._models import Severity, Violation
from frob.tickets._land import _dry_run_squash_preview_pre_commit_checks
from frob.tickets._models import LandError


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run a git command in `cwd`, asserting success -- test-only helper
    (mirrors tests/unit/test_land_compose.py's own `_run`)."""
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


@pytest.fixture
def scratch_land(tmp_path: Path) -> tuple[Path, Path]:
    """`(root, worktree)`: `root` is a bare-ish `main`-branch checkout with
    one committed file; `worktree` is a SEPARATE checkout of a `ticket`
    branch (created from `root`'s tip) that adds a second file -- the
    minimal shape `_dry_run_squash_preview_pre_commit_checks` needs to
    compose a real disposable squash preview of `worktree`'s branch onto
    `root`'s tip. `.frob/` is gitignored from the first commit, mirroring
    tests/unit/test_land_compose.py::scratch_repo's own T-3163 rationale --
    the composed preview takes `root`'s `ledger_lock` for its lifetime,
    which would otherwise show up as an untracked path in a porcelain
    check."""
    root = tmp_path / "root"
    root.mkdir()
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)
    (root / ".gitignore").write_text(".frob/\n")
    _run(["git", "add", ".gitignore"], root)
    _run(["git", "commit", "-q", "-m", "gitignore .frob/"], root)
    (root / "src").mkdir()
    (root / "src" / "existing.py").write_text("# base\n")
    _run(["git", "add", "src/existing.py"], root)
    _run(["git", "commit", "-q", "-m", "base"], root)

    worktree = tmp_path / "worktree"
    _run(
        ["git", "worktree", "add", "-q", "-b", "ticket", str(worktree), "main"], root
    )
    (worktree / "src" / "feature.py").write_text("# new in this land\n")
    _run(["git", "add", "src/feature.py"], worktree)
    _run(["git", "commit", "-q", "-m", "T-0001: add feature.py"], worktree)
    return root, worktree


class TestDryRunSquashPreviewPreCommitChecks:
    """T-5403's dry-run squash-preview check -- must catch what a real
    land's own `_run_pre_commit_checks` catches, and must never mutate
    `root` or `worktree` while doing it."""

    # frob:tests tests/ticket_land_suite/test_land_dry_run_squash_preview.py::TestDryRunSquashPreviewPreCommitChecks.test_dry_run_refuses_on_a_planted_selfaudit001_sink  # noqa: E501
    def test_dry_run_refuses_on_a_planted_selfaudit001_sink(
        self, scratch_land: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Positive control: a planted SELFAUDIT001 finding attributable to
        the land's own touched file (`src/feature.py`, the file this
        fixture's ticket branch adds) must refuse the dry-run preview with
        the SAME `LandError.PreLandUnscopedSweepFailed` a real land
        reports for the identical finding."""
        root, worktree = scratch_land
        pre_land_tip = _run(["git", "rev-parse", "main"], root).stdout.strip()
        finding = Violation(
            rule="SELFAUDIT001",
            severity=Severity.ERROR,
            file="design",
            line=1,
            message=(
                "SELFAUDIT001: self-audit family SYS100 node=testsuite: "
                "capability 'fs.read' observed at src/feature.py:1 but not "
                "declared"
            ),
        )
        monkeypatch.setattr(
            "frob.gates._sys.selfaudit_findings_touching",
            lambda root, files: (finding,),
        )
        monkeypatch.setattr(
            "frob.gates._sys.sys111_findings_touching", lambda root, files: ()
        )
        monkeypatch.setattr(
            "frob.gates._sys.docptr_findings_touching", lambda root, files: ()
        )

        result = _dry_run_squash_preview_pre_commit_checks(
            root, worktree, "T-0001", "main", pre_land_tip
        )

        assert result.is_err
        assert result.danger_err == LandError.PreLandUnscopedSweepFailed
        # Neither checkout was mutated by the preview.
        assert _run(["git", "status", "--porcelain"], root).stdout == ""
        assert _run(["git", "status", "--porcelain"], worktree).stdout == ""
        assert _run(["git", "rev-parse", "main"], root).stdout.strip() == pre_land_tip

    # frob:tests tests/ticket_land_suite/test_land_dry_run_squash_preview.py::TestDryRunSquashPreviewPreCommitChecks.test_dry_run_refuses_on_a_planted_doc006_pointer  # noqa: E501
    def test_dry_run_refuses_on_a_planted_doc006_pointer(
        self, scratch_land: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Positive control: a planted DOC006 (dangling doc pointer)
        finding attributable to the land's own touched file must likewise
        refuse the dry-run preview -- DOC006 is the OTHER family T-5403
        names (`docptr_findings_touching`), never evaluated by the pre-
        T-5403 dry-run path at all."""
        root, worktree = scratch_land
        pre_land_tip = _run(["git", "rev-parse", "main"], root).stdout.strip()
        finding = Violation(
            rule="DOC006",
            severity=Severity.ERROR,
            file="docs/guide.md",
            line=3,
            message="DOC006: file/path pointer in docs/guide.md:3 does not resolve",
        )
        monkeypatch.setattr(
            "frob.gates._sys.selfaudit_findings_touching", lambda root, files: ()
        )
        monkeypatch.setattr(
            "frob.gates._sys.sys111_findings_touching", lambda root, files: ()
        )
        monkeypatch.setattr(
            "frob.gates._sys.docptr_findings_touching",
            lambda root, files: (finding,),
        )

        result = _dry_run_squash_preview_pre_commit_checks(
            root, worktree, "T-0001", "main", pre_land_tip
        )

        assert result.is_err
        assert result.danger_err == LandError.PreLandUnscopedSweepFailed

    # frob:tests tests/ticket_land_suite/test_land_dry_run_squash_preview.py::TestDryRunSquashPreviewPreCommitChecks.test_clean_worktree_dry_run_stays_clean  # noqa: E501
    def test_clean_worktree_dry_run_stays_clean(
        self, scratch_land: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Negative control: with no findings from any of the three gate
        families, the preview must report `Ok(None)` -- a clean dry run
        stays clean, and `root`'s tip is unchanged."""
        root, worktree = scratch_land
        pre_land_tip = _run(["git", "rev-parse", "main"], root).stdout.strip()
        monkeypatch.setattr(
            "frob.gates._sys.selfaudit_findings_touching", lambda root, files: ()
        )
        monkeypatch.setattr(
            "frob.gates._sys.sys111_findings_touching", lambda root, files: ()
        )
        monkeypatch.setattr(
            "frob.gates._sys.docptr_findings_touching", lambda root, files: ()
        )

        result = _dry_run_squash_preview_pre_commit_checks(
            root, worktree, "T-0001", "main", pre_land_tip
        )

        assert result.is_ok
        assert _run(["git", "rev-parse", "main"], root).stdout.strip() == pre_land_tip
