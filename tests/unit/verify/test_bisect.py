"""Unit tests for `frob.verify._bisect` (T-1691): Tier 3 attribution
fallback -- binary-search a batch's ordered candidate commits over ONE
finding identity, converging in `log2(N)` scoped re-verifications
instead of a full gate re-run per candidate."""

from __future__ import annotations

import math
from pathlib import Path

from typani import Err, Ok

from frob.verify._bisect import (
    BisectError,
    bisect_unattributed_finding,
)
from tests.unit.verify.test_watermark import _init_git_repo_with_commits


def _content_verify_fn(culprit_index: int, shas: list[str]):
    """A real (not mocked) `VerifyAtCommit`: reads `file.txt` out of the
    detached SNAPSHOT worktree `bisect_unattributed_finding` spawns for
    each candidate, and reports the finding as present ("bad") once the
    checked-out commit is at or after `shas[culprit_index]` -- the exact
    monotonic good-then-bad shape a real regression bisect assumes.
    Counts its own calls (via the mutable `calls` list) so tests can
    assert the `log2(N)` step-count acceptance criterion directly."""
    calls: list[str] = []

    def verify(snapshot: Path, commit: str):
        calls.append(commit)
        text = (snapshot / "file.txt").read_text(encoding="utf-8")
        seen_index = int(text.split()[1])
        return Ok(seen_index >= culprit_index)

    return verify, calls


class TestBisectUnattributedFinding:
    """`bisect_unattributed_finding` (T-1691)."""

    def test_converges_to_the_known_culprit_within_log2_n_steps(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_bisect.py::bisect_unattributed_finding
        """Acceptance criterion (this ticket's own body): a batch with
        one known-bad commit and no symbolic attribution converges to
        that commit within `log2(N)` scoped verifications."""
        shas = _init_git_repo_with_commits(tmp_path, 16)
        culprit_index = 11
        verify_fn, calls = _content_verify_fn(culprit_index, shas)

        result = bisect_unattributed_finding(
            tmp_path, "FIND-001", shas, verify_fn, step_budget=20
        )
        assert result.is_ok, result.danger_err
        outcome = result.danger_ok
        assert outcome.is_attributed
        assert outcome.culprit_commit == shas[culprit_index]
        assert outcome.steps_used <= math.ceil(math.log2(len(shas))) + 1
        assert len(calls) == outcome.steps_used

    def test_converges_when_culprit_is_the_first_candidate(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_bisect.py::bisect_unattributed_finding
        shas = _init_git_repo_with_commits(tmp_path, 8)
        verify_fn, _calls = _content_verify_fn(0, shas)

        result = bisect_unattributed_finding(tmp_path, "FIND-002", shas, verify_fn)
        assert result.is_ok
        assert result.danger_ok.culprit_commit == shas[0]

    def test_converges_when_culprit_is_the_last_candidate(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_bisect.py::bisect_unattributed_finding
        shas = _init_git_repo_with_commits(tmp_path, 8)
        verify_fn, _calls = _content_verify_fn(len(shas) - 1, shas)

        result = bisect_unattributed_finding(tmp_path, "FIND-003", shas, verify_fn)
        assert result.is_ok
        assert result.danger_ok.culprit_commit == shas[-1]

    def test_single_candidate_batch_attributes_without_any_verify_call(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_bisect.py::bisect_unattributed_finding
        """`low == high` on entry -- the search loop never runs, so a
        one-commit batch attributes to its own sole candidate for free."""
        shas = _init_git_repo_with_commits(tmp_path, 1)
        verify_fn, calls = _content_verify_fn(0, shas)

        result = bisect_unattributed_finding(tmp_path, "FIND-004", shas, verify_fn)
        assert result.is_ok
        outcome = result.danger_ok
        assert outcome.culprit_commit == shas[0]
        assert outcome.steps_used == 0
        assert calls == []

    def test_empty_candidates_refuses(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_bisect.py::bisect_unattributed_finding
        def verify(_snapshot: Path, _commit: str):
            return Ok(True)

        result = bisect_unattributed_finding(tmp_path, "FIND-005", [], verify)
        assert result.is_err
        assert result.danger_err == BisectError.NoCandidates

    def test_non_positive_budget_refuses(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_bisect.py::bisect_unattributed_finding
        shas = _init_git_repo_with_commits(tmp_path, 4)

        def verify(_snapshot: Path, _commit: str):
            return Ok(True)

        result = bisect_unattributed_finding(
            tmp_path, "FIND-006", shas, verify, step_budget=0
        )
        assert result.is_err
        assert result.danger_err == BisectError.NonPositiveBudget

        result = bisect_unattributed_finding(
            tmp_path, "FIND-007", shas, verify, wall_clock_budget_s=0.0
        )
        assert result.is_err
        assert result.danger_err == BisectError.NonPositiveBudget

    def test_exhausted_step_budget_files_unattributed_naming_every_candidate(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_bisect.py::bisect_unattributed_finding
        """A step budget too small to converge degrades to a BOUNDED,
        honest `UNATTRIBUTED` outcome naming the WHOLE original
        candidate set -- never just the still-unresolved half (the
        module's own 'cannot verify is never verified' invariant) --
        rather than an unbounded search or a silent wrong answer."""
        shas = _init_git_repo_with_commits(tmp_path, 64)
        verify_fn, _calls = _content_verify_fn(40, shas)

        result = bisect_unattributed_finding(
            tmp_path, "FIND-008", shas, verify_fn, step_budget=1
        )
        assert result.is_ok
        outcome = result.danger_ok
        assert not outcome.is_attributed
        assert outcome.unattributed_candidates == tuple(shas)
        assert outcome.steps_used == 1

    def test_exhausted_wall_clock_budget_files_unattributed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_bisect.py::bisect_unattributed_finding
        shas = _init_git_repo_with_commits(tmp_path, 32)
        verify_fn, _calls = _content_verify_fn(20, shas)

        result = bisect_unattributed_finding(
            tmp_path,
            "FIND-009",
            shas,
            verify_fn,
            step_budget=100,
            wall_clock_budget_s=0.0000001,
        )
        assert result.is_ok
        outcome = result.danger_ok
        assert not outcome.is_attributed
        assert outcome.unattributed_candidates == tuple(shas)

    def test_inconclusive_verify_callback_degrades_to_unattributed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_bisect.py::bisect_unattributed_finding
        """A mid-search `Err` from `verify_fn` (the check itself could
        not produce a verdict) is NEVER silently treated as good or bad
        -- it degrades to the same bounded, whole-batch `UNATTRIBUTED`
        outcome as a budget exhaustion, never a guess."""
        shas = _init_git_repo_with_commits(tmp_path, 8)

        def verify(_snapshot: Path, _commit: str):
            return Err("could not run the reproduction check")

        result = bisect_unattributed_finding(tmp_path, "FIND-010", shas, verify)
        assert result.is_ok
        outcome = result.danger_ok
        assert not outcome.is_attributed
        assert outcome.unattributed_candidates == tuple(shas)

    def test_never_touches_the_root_checkout(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_bisect.py::bisect_unattributed_finding
        """Every candidate is verified against a DETACHED snapshot
        worktree, never `root` itself -- `root`'s own HEAD/working tree
        must be byte-identical before and after a bisect run, the module
        docstring's 'never move the root checkout' contract."""
        import subprocess

        shas = _init_git_repo_with_commits(tmp_path, 8)
        head_before = subprocess.run(
            ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        status_before = subprocess.run(
            ["git", "-C", str(tmp_path), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout

        verify_fn, _calls = _content_verify_fn(4, shas)
        result = bisect_unattributed_finding(tmp_path, "FIND-011", shas, verify_fn)
        assert result.is_ok

        head_after = subprocess.run(
            ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        status_after = subprocess.run(
            ["git", "-C", str(tmp_path), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        assert head_after == head_before
        assert status_after == status_before
