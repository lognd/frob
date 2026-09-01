import multiprocessing
import os
import signal
import sys
import time
from datetime import date
from pathlib import Path

import pytest

import frob.tickets._land as _land_mod
import frob.tickets._land_git_ops as _land_git_ops_mod
import frob.tickets._land_squash as _land_squash_mod
from frob.tickets import (
    Origin,
    TicketKind,
    TicketState,
    new_ticket,
    transition,
)
from frob.tickets._land import land
from frob.tickets._models import (
    LandError,
    Ticket,
)
from frob.tickets._store import (
    ledger_path,
    load_all,
)
from tests._write_unchecked import _write_ticket_unchecked  # noqa: E402
from tests.ticket_land_suite.conftest import (
    _commit_all,
    _failing_run_argv,
    _make_closeable,
    _run,
    _spec,
    _status_ignoring_frob,
    _t0907_child_land,
    _t2679_child_land,
    _t2679b_child_land,
)

pytestmark = pytest.mark.heavy_subprocess



# frob:ticket T-0907
class TestVerifiedResetRoot:
    """T-0907: `_verified_reset_root` replaces every bare `git reset --hard`
    unwind in `land`'s squash-apply stage. A bare reset resolves its target
    from whatever `HEAD` happens to be AT RESET TIME -- the real incident
    this closes was a killed land whose unwind reset main to a stale tip
    ~60 commits behind, because at reset time root's `HEAD` had already
    (somehow) drifted from what the run started with. `_verified_reset_root`
    resets to an EXPLICIT sha captured at run start instead, and refuses
    loudly -- performing NO reset at all -- if root's current tip no longer
    matches it."""

    def test_resets_to_the_explicit_pre_land_tip_when_current_matches(
        self, repo: Path
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestVerifiedResetRoot.test_resets_to_the_explicit_pre_land_tip_when_current_matches  # noqa: E501
        pre = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        (repo / "scratch.txt").write_text("staged but never committed\n")
        _run(["git", "add", "scratch.txt"], repo)

        result = _land_git_ops_mod._verified_reset_root(repo, pre, "T-TEST")
        assert result.is_ok, result.err
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == pre
        assert _status_ignoring_frob(repo) == ""

    def test_refuses_and_does_not_reset_when_current_tip_has_drifted(
        self, repo: Path
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestVerifiedResetRoot.test_refuses_and_does_not_reset_when_current_tip_has_drifted  # noqa: E501
        pre = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        (repo / "another.txt").write_text("a real commit made after pre was captured\n")
        _commit_all(repo, "advance main past the recorded pre-land tip")
        drifted_tip = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert drifted_tip != pre

        result = _land_git_ops_mod._verified_reset_root(repo, pre, "T-TEST")
        assert result.is_err
        assert result.danger_err == LandError.GitFailed
        # NOT reset -- the drifted commit must still be there, untouched.
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == drifted_tip

    def test_drift_refusal_still_unstages_the_index(self, repo: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestVerifiedResetRoot.test_drift_refusal_still_unstages_the_index  # noqa: E501
        """T-1740: the 2026-08-07 incident -- a refused land used to leave
        its own staged squash content sitting in root's index forever on
        the drift path, because a full `reset --hard` there is unsafe (it
        could destroy the concurrent commit that caused the drift). The
        fix unstages (never touches HEAD or the concurrent commit) even
        though it cannot fully unwind."""
        pre = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        # Land's own staged squash content, still in the index.
        (repo / "land_staged.txt").write_text("land's own staged squash content\n")
        _run(["git", "add", "land_staged.txt"], repo)
        # A concurrent, unrelated real commit that moved HEAD past `pre`.
        (repo / "concurrent.txt").write_text("a real concurrent commit\n")
        _commit_all(repo, "advance main past the recorded pre-land tip")
        drifted_tip = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert drifted_tip != pre

        result = _land_git_ops_mod._verified_reset_root(repo, pre, "T-TEST")
        assert result.is_err
        assert result.danger_err == LandError.GitFailed
        # The concurrent commit survives untouched -- never reset.
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == drifted_tip
        assert (repo / "concurrent.txt").exists()
        # But the index no longer holds land's own staged content -- a
        # bystander's next bare `git commit` cannot sweep it up anymore.
        staged = _run(["git", "diff", "--cached", "--name-only"], repo).stdout.strip()
        assert staged == ""

    def test_unstage_index_only_never_moves_head_or_touches_tracked_content(
        self, repo: Path
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestVerifiedResetRoot.test_unstage_index_only_never_moves_head_or_touches_tracked_content  # noqa: E501
        head_before = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        (repo / "new_staged.txt").write_text("new staged file\n")
        _run(["git", "add", "new_staged.txt"], repo)

        result = _land_git_ops_mod._unstage_index_only(repo)
        assert result.is_ok, result.err
        # HEAD never moved.
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == head_before
        # Unstaged, but the file itself (an untracked leftover) still exists.
        staged = _run(["git", "diff", "--cached", "--name-only"], repo).stdout.strip()
        assert staged == ""
        assert (repo / "new_staged.txt").exists()


# frob:ticket T-2947
class TestDriftRefusalRestoresModifiedTrackedContent:
    """T-2947: the real incident -- a drift-refused land used to leave a
    MODIFIED TRACKED file's edited bytes sitting in root's working tree
    after `_unstage_index_only` (a bare `git reset` never touches
    working-tree content, only the index). For an ordinary bystander
    file that is cosmetic; for a ticket LEDGER file the squash already
    wrote `state: done` into before drift was detected, it is a false
    `done` legible to any on-disk reader while `git show HEAD:...`
    (correctly) shows nothing of the sort -- reproduces the real
    `GitFailed: refused to unwind` failure, not an approximation."""

    def test_must_fire_modified_tracked_ledger_file_restored_to_head(
        self, repo: Path
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestDriftRefusalRestoresModifiedTrackedContent.test_must_fire_modified_tracked_ledger_file_restored_to_head  # noqa: E501
        """Reproduces the exact T-2947 shape: a TRACKED ticket ledger file
        (already committed with `state: queued`) is modified in-place by
        this land's own squash (simulating the finalize write promoting
        it to `state: done`) and staged, matching a real `git merge
        --squash --no-commit` -- then a concurrent sibling land advances
        `root`'s real HEAD past this run's recorded `pre_land_tip`. Must-
        fire: after the drift refusal, the ledger file's ON-DISK content
        must show the COMMITTED (pre-squash) state, never the staged
        `done` text -- the false-done incident this ticket closes."""
        ledger = repo / "tickets.md"
        ledger.write_text("T-9001 state=queued\n")
        _commit_all(repo, "seed ledger at queued")
        pre = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        # A concurrent, unrelated sibling land commits and advances HEAD
        # past `pre` FIRST -- reproducing the actual race timeline: this
        # run captured `pre_land_tip` before it started its own long-
        # running squash-merge/staging, and the sibling's commit lands
        # (through the same shared root's working directory, serialized
        # by the OTHER land holding the lock ahead of this one resuming)
        # BEFORE this run's own squash gets around to staging its content
        # against what was, at capture time, believed to still be the
        # current tip. The sibling never touches `tickets.md` -- only its
        # own file.
        (repo / "sibling.txt").write_text("a real concurrent land\n")
        _run(["git", "add", "sibling.txt"], repo)
        _run(
            ["git", "commit", "-q", "-m", "concurrent sibling land advances main"],
            repo,
        )
        drifted_tip = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert drifted_tip != pre

        # THIS run's own squash-merge now stages its finalize write (the
        # promotion to `done`) against the working tree it still holds --
        # exactly what `_squash_and_splice_ledger[_v2]` does before the
        # final commit, and exactly why the drift is only discovered by
        # `_verified_reset_root` AFTER this staging has already happened.
        ledger.write_text("T-9001 state=done\n")
        _run(["git", "add", "tickets.md"], repo)

        result = _land_git_ops_mod._verified_reset_root(repo, pre, "T-TEST")

        assert result.is_err
        assert result.danger_err == LandError.GitFailed
        # The concurrent commit survives -- never reset.
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == drifted_tip
        # The must-fire assertion: the ledger's ON-DISK content must NOT
        # show the staged `done` text -- it must match what HEAD actually
        # commits (still `queued`, since the sibling never touched it).
        assert ledger.read_text() == "T-9001 state=queued\n"
        assert "done" not in ledger.read_text()
        # Nothing left staged either (T-1740's existing guarantee).
        staged = _run(["git", "diff", "--cached", "--name-only"], repo).stdout.strip()
        assert staged == ""

    def test_must_still_pass_untracked_leftover_is_not_touched(
        self, repo: Path
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestDriftRefusalRestoresModifiedTrackedContent.test_must_still_pass_untracked_leftover_is_not_touched  # noqa: E501
        """A brand-new, never-committed file this land staged (T-1740's
        own precedent) is left alone exactly as before -- it cannot
        manufacture a false ledger read, so restoring it would only mean
        destroying content nothing else needs touched."""
        pre = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        (repo / "new_file.txt").write_text("a genuinely new file\n")
        _run(["git", "add", "new_file.txt"], repo)
        (repo / "concurrent.txt").write_text("a real concurrent commit\n")
        _commit_all(repo, "advance main past the recorded pre-land tip")
        drifted_tip = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        result = _land_git_ops_mod._verified_reset_root(repo, pre, "T-TEST")

        assert result.is_err
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == drifted_tip
        assert (repo / "new_file.txt").read_text() == "a genuinely new file\n"

    def test_no_drift_no_restore_needed(self, repo: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestDriftRefusalRestoresModifiedTrackedContent.test_no_drift_no_restore_needed  # noqa: E501
        """Must-still-pass: the ordinary, no-drift path is completely
        unaffected by this fix -- `_verified_reset_root` still succeeds
        and fully hard-resets when there is no concurrent drift."""
        tracked = repo / "tracked.txt"
        tracked.write_text("original\n")
        _commit_all(repo, "seed tracked file")
        pre = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        tracked.write_text("staged but never committed\n")
        _run(["git", "add", "tracked.txt"], repo)

        result = _land_git_ops_mod._verified_reset_root(repo, pre, "T-TEST")

        assert result.is_ok, result.err
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == pre
        assert tracked.read_text() == "original\n"
        assert _status_ignoring_frob(repo) == ""




# frob:ticket T-1740
class TestCommitSquashApplyUnwindsOnCommitFailure:
    """T-1740's audit found this the ONE real gap: every other failure
    path in the squash-apply pipeline already unwinds via
    `_verified_reset_root`, but `_commit_squash_apply` -- the LAST step,
    the actual `git commit` -- used to just tell the operator to clean up
    root by hand on failure, leaving the fully-staged squash sitting in
    the index."""

    def test_commit_failure_unwinds_the_staged_squash(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestCommitSquashApplyUnwindsOnCommitFailure.test_commit_failure_unwinds_the_staged_squash  # noqa: E501
        pre = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        (repo / "staged_by_land.txt").write_text("staged squash content\n")
        _run(["git", "add", "staged_by_land.txt"], repo)

        ticket = Ticket(
            id="T-9999",
            title="test commit failure unwind",
            state=TicketState.IN_PROGRESS,
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
        )

        _failing_run_argv(
            monkeypatch,
            lambda argv: "commit" in argv and "-m" in argv,
        )

        result = _land_squash_mod._commit_squash_apply(
            repo, ticket, "T-9999", pre_land_tip=pre
        )
        assert result.is_err
        assert result.danger_err == LandError.CommitFailed
        # The staged squash was unwound -- root is back to its pre-land
        # tip, clean, nothing left for a bystander's next commit to sweep.
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == pre
        assert _status_ignoring_frob(repo) == ""



# frob:ticket T-1940
class TestCommittedDiffGuardRegistryCompleteness:
    """T-1940: generalizes T-1932's worked pattern (a hand-copied post-
    mutation twin per guard) into a registry (`_land_mod.
    _COMMITTED_DIFF_GUARDS`) plus a structural test -- this class -- that
    fails the moment a NEW committed-diff-reading guard is added to
    either `_land_precheck` or `_land_precheck_remaining_checks` without
    an explicit registry entry (a post-mutation twin, or a stated
    exemption reason), closing T-1932 acceptance criterion 4
    mechanically instead of relying on a future author remembering the
    worked example by hand."""

    #: Every guard-calling function name this test currently expects to
    #: find invoked inside `_land_precheck`/`_land_precheck_remaining_
    #: checks`'s own source -- the fixed point this test pins so that
    #: `_COMMITTED_DIFF_GUARDS` and the real call sites can never
    #: silently diverge from each other.
    _EXPECTED_CALL_SITES = frozenset(
        {
            "_check_already_landed",
            "_refuse_anchor_terminal_land",
            "_check_live_tracker_citations",
            "_check_passenger_tickets",
            "_check_cross_ticket_leakage",
            "_check_orphaned_evidence_deletion",
            "_check_mutation_evidence",
        }
    )

    # frob:ticket T-2017
    def test_every_call_site_guard_is_registered(self) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestCommittedDiffGuardRegistryCompleteness.test_every_call_site_guard_is_registered  # noqa: E501
        # T-1940 (MUST FAIL if a guard call is added to _land_precheck/
        # _land_precheck_remaining_checks without a matching registry
        # entry, or removed from source without removing its entry):
        # cross-references the FIXED expected call-site set above against
        # the registry's own tracked names, in both directions.
        registered = frozenset(guard.name for guard in _land_mod._COMMITTED_DIFF_GUARDS)
        missing_from_registry = self._EXPECTED_CALL_SITES - registered
        assert not missing_from_registry, (
            f"guard(s) called in the land preflight sequence but not "
            f"registered in _COMMITTED_DIFF_GUARDS: {sorted(missing_from_registry)}"
        )
        stale_in_registry = registered - self._EXPECTED_CALL_SITES
        assert not stale_in_registry, (
            f"guard(s) registered in _COMMITTED_DIFF_GUARDS but no longer "
            f"called anywhere in the land preflight sequence (stale entry, "
            f"update _EXPECTED_CALL_SITES or remove the registry row): "
            f"{sorted(stale_in_registry)}"
        )

    # frob:ticket T-2017
    def test_every_registry_entry_has_a_twin_or_a_stated_reason(self) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestCommittedDiffGuardRegistryCompleteness.test_every_registry_entry_has_a_twin_or_a_stated_reason  # noqa: E501
        # T-1940: the actual acceptance-criterion enforcement -- a
        # registry row is never allowed to have BOTH fields empty (a
        # silent gap), only one or the other (a closed hazard, or an
        # honestly acknowledged open one).
        for guard in _land_mod._COMMITTED_DIFF_GUARDS:
            has_twin = guard.post_mutation_check is not None
            has_reason = bool(guard.exemption_reason)
            assert has_twin or has_reason, (
                f"{guard.name} has neither a post_mutation_check twin nor "
                f"an exemption_reason -- every _COMMITTED_DIFF_GUARDS row "
                f"must have one or the other"
            )
            if has_twin:
                assert hasattr(_land_mod, guard.post_mutation_check), (
                    f"{guard.name}'s registered post_mutation_check "
                    f"{guard.post_mutation_check!r} does not exist in "
                    f"frob.tickets._land"
                )

    # frob:ticket T-2017
    def test_registered_twins_are_actually_wired_into_the_land_sequence(
        self, repo: Path
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestCommittedDiffGuardRegistryCompleteness.test_registered_twins_are_actually_wired_into_the_land_sequence  # noqa: E501
        # A registry entry claiming a twin exists is only meaningful if
        # `_land_locked` actually CALLS it -- source-inspects `_land_
        # locked` for each registered twin's own name, the same
        # completeness spirit as the call-site test above but for the
        # SECOND (post-mutation) call site instead of the first
        # (preflight) one.
        import inspect

        source = inspect.getsource(_land_mod._land_locked)
        for guard in _land_mod._COMMITTED_DIFF_GUARDS:
            if guard.post_mutation_check is None:
                continue
            assert guard.post_mutation_check in source, (
                f"{guard.name}'s registered twin {guard.post_mutation_check!r} "
                f"is not called anywhere in _land_locked's own source"
            )


# frob:ticket T-0907
class TestLandRepairMarker:
    """T-0907: `_repair_stale_land_marker` reconciles a crashed land's
    leftover land-repair marker at the start of the NEXT `land()` call
    against the same root/ticket."""

    def test_no_marker_is_a_silent_no_op(self, repo: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestLandRepairMarker.test_no_marker_is_a_silent_no_op  # noqa: E501
        result = _land_mod._repair_stale_land_marker(repo)
        assert result.is_ok

    def test_repair_resets_root_when_current_tip_matches_the_marker(
        self, repo: Path
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestLandRepairMarker.test_repair_resets_root_when_current_tip_matches_the_marker  # noqa: E501
        pre = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        _land_mod._write_land_repair_marker(repo, "T-9999", pre)
        (repo / "leftover.txt").write_text("leftover staged squash content\n")
        _run(["git", "add", "leftover.txt"], repo)

        result = _land_mod._repair_stale_land_marker(repo)
        assert result.is_ok, result.err
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == pre
        assert _status_ignoring_frob(repo) == ""
        marker = _land_mod._land_repair_marker_path(repo, "T-9999")
        assert not marker.exists()

    # frob:ticket T-1963
    def test_repair_recovers_even_when_current_tip_has_drifted_from_the_marker(
        self, repo: Path
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestLandRepairMarker.test_repair_recovers_even_when_current_tip_has_drifted_from_the_marker  # noqa: E501
        # T-1963 (MUST FAIL on the pre-fix code): a marker's recorded tip
        # is stale because a DIFFERENT land legitimately committed onto
        # root while this one sat crashed -- the ordinary shape under
        # parallel dispatch, where lands are near-continuous. Repair must
        # succeed anyway, resetting to CURRENT HEAD (never the stale
        # recorded tip, which would destroy the commit landed in
        # between), leaving root clean and immediately landable by
        # another agent -- no human intervention required.
        pre = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        _land_mod._write_land_repair_marker(repo, "T-9999", pre)
        # A DIFFERENT, unrelated land commits for real while T-9999 sits
        # crashed -- root's tip legitimately advances past the marker
        # (staged/committed explicitly, so it never picks up the crashed
        # run's own leftover staged content added next).
        (repo / "advance.txt").write_text("a real commit landed since the marker\n")
        _run(["git", "add", "advance.txt"], repo)
        _run(
            [
                "git",
                "commit",
                "-q",
                "-m",
                "advance main past the marker's recorded tip",
            ],
            repo,
        )
        drifted = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert drifted != pre
        # The crashed run's own leftover staged garbage, left sitting on
        # top of the now-drifted tip -- exactly what a crashed land's
        # uncommitted squash-staging looks like from the next `land()`
        # call's point of view.
        (repo / "leftover.txt").write_text("leftover staged squash content\n")
        _run(["git", "add", "leftover.txt"], repo)

        result = _land_mod._repair_stale_land_marker(repo)

        assert result.is_ok, result.err
        # The drifted (legitimately landed) commit survives untouched.
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == drifted
        assert (repo / "advance.txt").exists()
        # Root is clean and the marker is cleared -- immediately landable
        # by another agent, no manual intervention.
        assert _status_ignoring_frob(repo) == ""
        marker = _land_mod._land_repair_marker_path(repo, "T-9999")
        assert not marker.exists()



# frob:ticket T-2679
class TestFinalizeRepairMarker:
    """T-2679: `_repair_stale_finalize_markers` reconciles a crashed
    land's leftover finalize-repair marker at the start of the NEXT
    `land()` call against the same root, for ANY ticket -- the visibility
    aid for the "terminal state written to a worktree, but root never
    received the matching commit" window `_write_finalize_repair_marker`
    brackets (before `_land_finalize_and_close`, cleared in a `finally`
    right after)."""

    def test_no_marker_is_a_silent_no_op(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestFinalizeRepairMarker.test_no_marker_is_a_silent_no_op  # noqa: E501
        with caplog.at_level("ERROR", logger="frob.tickets._land"):
            _land_mod._repair_stale_finalize_markers(repo)
        assert not [r for r in caplog.records if r.levelname == "ERROR"]

    def test_repair_logs_loudly_when_worktree_still_shows_done_but_root_does_not(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestFinalizeRepairMarker.test_repair_logs_loudly_when_worktree_still_shows_done_but_root_does_not  # noqa: E501
        # T-2679's own measured shape: a marker survives a crashed land,
        # AND root's own ledger has no record of the ticket at all (the
        # squash-apply never ran) -- exactly "state=done recorded
        # somewhere, zero code on main".
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-crash", str(wt)], repo)
        created = new_ticket(wt, _spec("Add crashy", scope=("src/crashy.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "close it")
        _land_mod._write_finalize_repair_marker(repo, tid, wt)

        with caplog.at_level("ERROR", logger="frob.tickets._land"):
            _land_mod._repair_stale_finalize_markers(repo)

        error_records = [r for r in caplog.records if r.levelname == "ERROR"]
        assert any(tid in r.message and str(wt) in r.message for r in error_records), [
            r.message for r in error_records
        ]
        marker = _land_mod._finalize_repair_marker_path(repo, tid)
        assert not marker.exists()

    def test_repair_is_silent_when_root_already_shows_the_ticket_done(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestFinalizeRepairMarker.test_repair_is_silent_when_root_already_shows_the_ticket_done  # noqa: E501
        # The self-healed case: a retry (or a manual recovery) already
        # landed the ticket for real onto root BEFORE this reconciliation
        # ever ran -- no anomaly to report.
        created = new_ticket(repo, _spec("Widget"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(repo, tid)
        assert transition(repo, tid, TicketState.DONE, covers_scope=True).is_ok
        _commit_all(repo, "close it for real")
        _land_mod._write_finalize_repair_marker(repo, tid, repo.parent / "gone-wt")

        with caplog.at_level("ERROR", logger="frob.tickets._land"):
            _land_mod._repair_stale_finalize_markers(repo)

        assert not [r for r in caplog.records if r.levelname == "ERROR"]
        marker = _land_mod._finalize_repair_marker_path(repo, tid)
        assert not marker.exists()


# frob:ticket T-1523
class TestPostLandVerifyPendingMarker:
    """T-1523: the post-commit twin of `TestLandRepairMarker` above --
    `_stale_post_land_verify_markers` reads back whatever `_write_post_
    land_verify_marker` recorded, read-only, for `_land_cmd._land_core`'s
    own `_report_stale_post_land_verify_markers` to reconcile at the start
    of the NEXT invocation."""

    def test_no_marker_is_a_silent_empty_result(self, repo: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestPostLandVerifyPendingMarker.test_no_marker_is_a_silent_empty_result  # noqa: E501
        assert _land_mod._stale_post_land_verify_markers(repo) == ()

    def test_stale_marker_reports_verified_true_when_commit_is_a_clean_ancestor(
        self, repo: Path
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestPostLandVerifyPendingMarker.test_stale_marker_reports_verified_true_when_commit_is_a_clean_ancestor  # noqa: E501
        sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        _land_mod._write_post_land_verify_marker(repo, "T-9999", sha)

        found = _land_mod._stale_post_land_verify_markers(repo)
        assert found == (("T-9999", sha),)

        # Write + clear round-trips cleanly, like the T-0907 marker does.
        _land_mod._clear_post_land_verify_marker(repo, "T-9999")
        assert _land_mod._stale_post_land_verify_markers(repo) == ()

    def test_orphaned_marker_from_a_killed_prior_run_is_reported_and_cleared(
        self, repo: Path
    ) -> None:
        """The integration shape: a marker left behind by a "killed"
        prior land is picked up by `_land_cmd._land_core`'s own
        reconciliation call the NEXT time `frob ticket land` runs for a
        DIFFERENT ticket -- reported via a `LAND-PROOF-RECOVERED:` log
        line and cleared, never blocking the new ticket's own land."""
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestPostLandVerifyPendingMarker.test_orphaned_marker_from_a_killed_prior_run_is_reported_and_cleared  # noqa: E501
        from frob.app.ticket_runner._land_cmd import (
            _report_stale_post_land_verify_markers,
        )

        pre_existing_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        _land_mod._write_post_land_verify_marker(repo, "T-8888", pre_existing_sha)
        marker_path = _land_mod._land_verify_pending_marker_path(repo, "T-8888")
        assert marker_path.exists()

        _report_stale_post_land_verify_markers(repo)

        # Reconciled (cleared) regardless of verified outcome -- a
        # DIFFERENT, currently-landing ticket must never be blocked by a
        # PRIOR, unrelated ticket's leftover marker.
        assert not marker_path.exists()




# frob:ticket T-0907
class TestSigkillMidStaging:
    """T-0907's own regression lock: a real `SIGKILL` (uncatchable by any
    in-process signal handler, unlike SIGTERM) delivered while `land()` is
    mid-squash-apply onto root must leave root's tip completely unchanged,
    and the crash must be repairable by the next `land()` call for the same
    ticket -- the incident this ticket exists to close was the opposite: a
    killed land's own unwind reset main to a stale tip ~60 commits behind."""

    def test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry(
        self, repo: Path
    ) -> None:
        if sys.platform == "win32":
            pytest.skip("POSIX-only (T-3244)")
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestSigkillMidStaging.test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-kill", str(wt)], repo)
        created = new_ticket(wt, _spec("Add killable", scope=("src/killable.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "killable.py").write_text("# new file\n")
        _commit_all(wt, "add killable")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        ready_path = repo.parent / "ready.flag"

        ctx = multiprocessing.get_context("fork")
        proc = ctx.Process(target=_t0907_child_land, args=(repo, tid, wt, ready_path))
        proc.start()
        deadline = time.monotonic() + 20
        while not ready_path.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert ready_path.exists(), "child land() never reached the squash-apply step"
        assert proc.pid is not None
        os.kill(proc.pid, signal.SIGKILL)
        proc.join(timeout=15)
        assert not proc.is_alive()

        # The kill must not have moved root's tip AT ALL.
        after_kill_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert after_kill_sha == before_main_sha

        # A land-repair marker must survive the kill, recording exactly
        # this run's pre-land tip.
        marker_dir = repo / ".frob" / "land-repair"
        marker_files = list(marker_dir.glob("*.json"))
        assert len(marker_files) == 1, marker_files

        # The killed run already finalized/renumbered the draft id (and
        # closed it) in the worktree before its own crash -- exactly the
        # T-0795 retry shape (TestLandRetryAfterFinalizeThenFail above):
        # the retry addresses the ticket by its now-finalized id.
        wt_tickets = load_all(wt).danger_ok
        final_id = next(i for i, t in wt_tickets.items() if t.state == TicketState.DONE)

        # The next `land()` call for the same ticket reconciles the marker
        # (root's tip still matches it -- the crash happened before any
        # commit landed on root) and actually lands.
        result = land(repo, final_id, wt, dry_run=False)
        assert result.is_ok, result.err
        assert not marker_files[0].exists()
        assert (repo / "src" / "killable.py").exists()
        after_retry_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert after_retry_sha != before_main_sha
        assert _status_ignoring_frob(repo) == ""

    # frob:ticket T-2564
    def test_unrelated_land_does_not_absorb_a_killed_lands_staged_content(
        self, repo: Path
    ) -> None:
        if sys.platform == "win32":
            pytest.skip("POSIX-only (T-3244)")
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestSigkillMidStaging.test_unrelated_land_does_not_absorb_a_killed_lands_staged_content  # noqa: E501
        """T-2564: the hazard a bare abandoned-staged-content symptom does
        NOT by itself prove -- that a DIFFERENT, unrelated ticket's own
        `land()` call, running against the same `root` shortly after the
        kill, could sweep the crashed run's still-staged garbage into ITS
        OWN commit (`_land_repair_marker`'s window is per-`root`, not
        per-ticket, so this is the real question T-2564 was filed to
        answer). It does not: `_repair_stale_land_marker` runs at the very
        start of EVERY `land()` call, before that call's own DirtyMain
        check or its own staging, so the second ticket's land reconciles
        the first ticket's leftover marker+staged content (discarding it,
        per `_reconcile_one_land_repair_marker`) BEFORE it stages anything
        of its own -- structurally, not by luck."""
        wt_a = repo.parent / "wt-a"
        _run(["git", "worktree", "add", "-b", "feature-kill", str(wt_a)], repo)
        created_a = new_ticket(wt_a, _spec("Add killable", scope=("src/killable.py",)))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        _make_closeable(wt_a, tid_a)
        (wt_a / "src" / "killable.py").write_text("# new file\n")
        _commit_all(wt_a, "add killable")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        ready_path = repo.parent / "ready.flag"

        ctx = multiprocessing.get_context("fork")
        proc = ctx.Process(
            target=_t0907_child_land, args=(repo, tid_a, wt_a, ready_path)
        )
        proc.start()
        deadline = time.monotonic() + 20
        while not ready_path.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert ready_path.exists(), "child land() never reached the squash-apply step"
        assert proc.pid is not None
        os.kill(proc.pid, signal.SIGKILL)
        proc.join(timeout=15)
        assert not proc.is_alive()
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        marker_dir = repo / ".frob" / "land-repair"
        assert len(list(marker_dir.glob("*.json"))) == 1

        # A SECOND, completely unrelated ticket lands against the SAME
        # root while T-9999-A's marker+staged garbage still sits there.
        wt_b = repo.parent / "wt-b"
        _run(["git", "worktree", "add", "-b", "feature-unrelated", str(wt_b)], repo)
        created_b = new_ticket(
            wt_b, _spec("Unrelated feature", scope=("src/unrelated.py",))
        )
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id
        _make_closeable(wt_b, tid_b)
        (wt_b / "src" / "unrelated.py").write_text("# unrelated feature\n")
        _commit_all(wt_b, "add unrelated")

        result_b = land(repo, tid_b, wt_b, dry_run=False)
        assert result_b.is_ok, result_b.err

        # The killed ticket's marker is gone (reconciled by B's own land,
        # not B's own concern) and its file never reached main.
        assert not list(marker_dir.glob("*.json"))
        assert not (repo / "src" / "killable.py").exists()

        # B's own new commit(s) carry ONLY B's own file -- the killed
        # run's abandoned staged content was discarded, never absorbed as
        # a passenger of B's own land (may be more than one commit: the
        # squash-apply plus a separate ledger record-commit).
        changed = _run(
            ["git", "diff", "--name-only", before_main_sha, "HEAD"], repo
        ).stdout.splitlines()
        assert "src/unrelated.py" in changed
        assert "src/killable.py" not in changed
        assert _status_ignoring_frob(repo) == ""

        # The killed ticket's own retry, afterward, still lands cleanly.
        wt_tickets = load_all(wt_a).danger_ok
        final_id_a = next(
            i for i, t in wt_tickets.items() if t.state == TicketState.DONE
        )
        result_a = land(repo, final_id_a, wt_a, dry_run=False)
        assert result_a.is_ok, result_a.err
        assert (repo / "src" / "killable.py").exists()
        assert _status_ignoring_frob(repo) == ""

    # frob:ticket T-2679
    def test_sigkill_during_finalize_close_leaves_ticket_recoverable_not_a_silent_lie(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        if sys.platform == "win32":
            pytest.skip("POSIX-only (T-3244)")
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestSigkillMidStaging.test_sigkill_during_finalize_close_leaves_ticket_recoverable_not_a_silent_lie  # noqa: E501
        """T-2679's own positive control, ONE step earlier than T-0907's:
        a real `SIGKILL` delivered while `land()` is mid-
        `_land_finalize_and_close` -- AFTER the worktree's ticket.md has
        already been rewritten to `state: done` on disk but BEFORE that
        write is even committed to the worktree's own branch, and BEFORE
        `root` (main) has been touched in any way at all (squash-apply
        never starts). This is the exact shape T-2671 measured: a
        terminal state that could plausibly be read as "done" with zero
        corresponding content on main. Required, both directions:
        (1) root's tip is completely unchanged by the kill: content stays
            absent, never a partial/corrupt land.
        (2) the T-2679 finalize-repair marker survives the kill and the
            NEXT `land()` call against this root (here, this same
            ticket's own retry) reconciles it LOUDLY -- the anomaly is
            surfaced, not silently lost.
        (3) the retry itself still reaches `done` on root exactly once,
            with no extra transition and no regression -- a normal
            successful land is unaffected by this fix."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-kill2", str(wt)], repo)
        created = new_ticket(wt, _spec("Add killable2", scope=("src/killable2.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "killable2.py").write_text("# new file\n")
        _commit_all(wt, "add killable2")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        ready_path = repo.parent / "ready2.flag"

        ctx = multiprocessing.get_context("fork")
        proc = ctx.Process(target=_t2679_child_land, args=(repo, tid, wt, ready_path))
        proc.start()
        deadline = time.monotonic() + 20
        while not ready_path.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert ready_path.exists(), "child land() never reached finalize-close"
        assert proc.pid is not None
        os.kill(proc.pid, signal.SIGKILL)
        proc.join(timeout=15)
        assert not proc.is_alive()

        # (1) root's tip is completely unchanged -- content stays absent.
        after_kill_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert after_kill_sha == before_main_sha
        assert not (repo / "src" / "killable2.py").exists()

        # A T-2679 finalize-repair marker must survive the kill.
        marker_dir = repo / ".frob" / "finalize-repair"
        marker_files = list(marker_dir.glob("*.json"))
        assert len(marker_files) == 1, marker_files

        # (2) the NEXT land() call against this root reconciles it loudly
        # -- naming the ticket, before it does anything else of its own.
        # The killed run already wrote (uncommitted, or committed
        # depending on exactly where the kill landed) `state: done` to
        # the worktree -- find it the same T-0795 way the T-0907 test
        # does.
        wt_tickets = load_all(wt).danger_ok
        done_ids = [i for i, t in wt_tickets.items() if t.state == TicketState.DONE]
        assert done_ids, "finalize-close never reached the DONE write at all"
        final_id = done_ids[0]

        with caplog.at_level("ERROR", logger="frob.tickets._land"):
            result = land(repo, final_id, wt, dry_run=False)
        assert result.is_ok, result.err
        # The marker was written under `tid`, the ORIGINAL (possibly
        # draft) id `land()` was called with -- `_land_finalize_and_close`
        # only renumbers to `final_id` INSIDE the window the marker
        # brackets, so the reconciliation log (keyed to the marker's own
        # filename) names `tid`, not `final_id`.
        error_records = [r for r in caplog.records if r.levelname == "ERROR"]
        assert any(tid in r.message for r in error_records), [
            r.message for r in error_records
        ]
        assert not marker_files[0].exists()

        # (3) reaches done on root exactly once, no regression.
        on_root = load_all(repo).danger_ok[final_id]
        assert on_root.state == TicketState.DONE
        assert (repo / "src" / "killable2.py").exists()
        after_retry_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert after_retry_sha != before_main_sha
        assert _status_ignoring_frob(repo) == ""

    # frob:ticket T-2679
    def test_normal_land_reaches_done_exactly_once_no_extra_transition(
        self, repo: Path
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestSigkillMidStaging.test_normal_land_reaches_done_exactly_once_no_extra_transition  # noqa: E501
        """The required OTHER direction: an ordinary, uninterrupted land
        must be completely unaffected by the T-2679 finalize-repair
        marker -- it is written and cleared within the same call, no
        extra ledger transition, no stray marker left behind, `done`
        reached exactly once."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-normal", str(wt)], repo)
        created = new_ticket(wt, _spec("Add normal", scope=("src/normal.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "normal.py").write_text("# new file\n")
        _commit_all(wt, "add normal")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err

        marker_dir = repo / ".frob" / "finalize-repair"
        assert not (marker_dir.is_dir() and list(marker_dir.glob("*.json")))
        landed = load_all(repo).danger_ok
        final_ids = [i for i, t in landed.items() if t.title == "Add normal"]
        assert len(final_ids) == 1
        assert landed[final_ids[0]].state == TicketState.DONE
        assert (repo / "src" / "normal.py").exists()

    # frob:ticket T-2679
    def test_sigkill_during_post_squash_reverification_leaves_ticket_recoverable(
        self, repo: Path
    ) -> None:
        if sys.platform == "win32":
            pytest.skip("POSIX-only (T-3244)")
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestSigkillMidStaging.test_sigkill_during_post_squash_reverification_leaves_ticket_recoverable  # noqa: E501
        """The coordinator's own live-fire control (a real T-2696
        reproduction, 2026-08-20): a land was killed not right after the
        squash-merge stages (T-0907's own test, above), but LATER, during
        the post-squash RE-VERIFICATION phase that runs before the final
        commit (`land()`'s own `pre_commit_sweep` hook, T-1514) -- a phase
        that can run long enough on its own to exceed a wrapper's timeout.
        `root` was left with the FULL, correct squash-apply staged in its
        index, uncommitted -- `tickets/<id>/ticket.md` read `state: done`
        in the working tree with no matching commit anywhere.

        This is squarely inside the SAME T-0907 land-repair-marker window
        `_write_land_repair_marker`/`_repair_stale_land_marker` already
        bracket (written before `_land_squash_apply` starts, which is
        BEFORE the squash-merge even runs, and cleared only once THAT
        whole call -- staging, `pre_commit_sweep`, the T-0463 completeness
        assertion, and the final commit -- returns): no new production
        code is needed to make this window safe, only proof that it
        already is, at the SPECIFIC point the coordinator's own incident
        actually hit. Required, both directions, mirroring T-2679's other
        SIGKILL control:
        (1) root's tip is unchanged by the kill -- the staged content
            (correct or not) never becomes a partial commit.
        (2) the marker survives and the NEXT `land()` call for this same
            root reconciles it (T-0907's existing `_repair_stale_land_
            marker`) and the ticket lands cleanly on retry -- never left
            terminal with no matching commit."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-reverify", str(wt)], repo)
        created = new_ticket(wt, _spec("Add reverify", scope=("src/reverify.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "reverify.py").write_text("# new file\n")
        _commit_all(wt, "add reverify")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        ready_path = repo.parent / "ready3.flag"

        ctx = multiprocessing.get_context("fork")
        proc = ctx.Process(target=_t2679b_child_land, args=(repo, tid, wt, ready_path))
        proc.start()
        deadline = time.monotonic() + 20
        while not ready_path.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert ready_path.exists(), "child land() never reached pre_commit_sweep"
        assert proc.pid is not None
        os.kill(proc.pid, signal.SIGKILL)
        proc.join(timeout=15)
        assert not proc.is_alive()

        # (1) root's tip is completely unchanged -- staged, never committed.
        after_kill_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert after_kill_sha == before_main_sha
        marker_dir = repo / ".frob" / "land-repair"
        assert len(list(marker_dir.glob("*.json"))) == 1

        # (2) the ticket's worktree-side write already reads `done` (the
        # exact incident shape: a terminal state with, at this instant,
        # no matching commit anywhere) -- and the NEXT land() call
        # reconciles + actually lands it, never leaving it a silent lie.
        wt_tickets = load_all(wt).danger_ok
        final_id = next(i for i, t in wt_tickets.items() if t.state == TicketState.DONE)

        result = land(repo, final_id, wt, dry_run=False)
        assert result.is_ok, result.err
        assert not list(marker_dir.glob("*.json"))
        on_root = load_all(repo).danger_ok[final_id]
        assert on_root.state == TicketState.DONE
        assert (repo / "src" / "reverify.py").exists()
        after_retry_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert after_retry_sha != before_main_sha
        assert _status_ignoring_frob(repo) == ""



class TestTick005LandRegressions:
    """T-0631: `_tick005_land_regressions` -- the TICK005-backed regression
    sweep run directly around a land's own squash-splice (mirrors
    `frob.gates._tick005_merge_state_regression`'s semantics without a
    two-parent merge commit, since a squash-apply never produces one)."""

    def test_no_regression_when_terminal_ticket_stays_terminal(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestTick005LandRegressions.test_no_regression_when_terminal_ticket_stays_terminal  # noqa: E501
        created = new_ticket(tmp_path, _spec("Widget"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(tmp_path, tid)
        pre_text = ledger_path(tmp_path).read_text()

        regressions = _land_squash_mod._tick005_land_regressions(
            pre_text, pre_text, frozenset()
        )
        assert regressions == ()

    def test_detects_terminal_ticket_regressed_to_non_terminal(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestTick005LandRegressions.test_detects_terminal_ticket_regressed_to_non_terminal  # noqa: E501
        created = new_ticket(tmp_path, _spec("Widget"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(tmp_path, tid)
        assert transition(tmp_path, tid, TicketState.DONE, covers_scope=True).is_ok
        pre_text = ledger_path(tmp_path).read_text()

        # Simulate the hand-resolved-conflict incident class: the "post"
        # ledger keeps the same id but reverts it to a non-terminal state.
        regressed = new_ticket(tmp_path, _spec("Widget2")).danger_ok
        assert _write_ticket_unchecked(
            tmp_path,
            regressed.model_copy(update={"id": tid, "state": TicketState.IN_PROGRESS}),
        ).is_ok
        post_text = ledger_path(tmp_path).read_text()

        regressions = _land_squash_mod._tick005_land_regressions(
            pre_text, post_text, frozenset()
        )
        assert regressions == (tid,)

    def test_archived_ids_are_excluded(self, tmp_path: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestTick005LandRegressions.test_archived_ids_are_excluded  # noqa: E501
        created = new_ticket(tmp_path, _spec("Widget"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(tmp_path, tid)
        assert transition(tmp_path, tid, TicketState.DONE, covers_scope=True).is_ok
        pre_text = ledger_path(tmp_path).read_text()

        regressed = new_ticket(tmp_path, _spec("Widget2")).danger_ok
        assert _write_ticket_unchecked(
            tmp_path,
            regressed.model_copy(update={"id": tid, "state": TicketState.IN_PROGRESS}),
        ).is_ok
        post_text = ledger_path(tmp_path).read_text()

        # An archived id is exempt -- it is expected to be absent/stale in
        # the active ledger, not a regression.
        regressions = _land_squash_mod._tick005_land_regressions(
            pre_text, post_text, frozenset({tid})
        )
        assert regressions == ()

    def test_malformed_text_degrades_to_no_regressions(self, tmp_path: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestTick005LandRegressions.test_malformed_text_degrades_to_no_regressions  # noqa: E501
        malformed = "# Tickets\n\n<!-- ticket:T-0001 -->\nno frontmatter here\n"
        created = new_ticket(tmp_path, _spec("Widget"))
        assert created.is_ok
        valid_text = ledger_path(tmp_path).read_text()

        assert (
            _land_squash_mod._tick005_land_regressions(
                malformed, valid_text, frozenset()
            )
            == ()
        )
        assert (
            _land_squash_mod._tick005_land_regressions(
                valid_text, malformed, frozenset()
            )
            == ()
        )



class TestLandRefusesOnTerminalStateRegression:
    """T-0631: `land()` itself refuses (and unwinds root back to its
    pre-land tip) when the TICK005-backed regression sweep finds a
    regression in its own squash-splice."""

    def test_land_refuses_and_unwinds_when_sweep_finds_a_regression(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_verify_reset.py::TestLandRefusesOnTerminalStateRegression.test_land_refuses_and_unwinds_when_sweep_finds_a_regression  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-tick005", str(wt)], repo)
        created = new_ticket(wt, _spec("Add sprocket", scope=("src/sprocket.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "sprocket.py").write_text("# new sprocket\n")
        _commit_all(wt, "add sprocket")

        pre_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        monkeypatch.setattr(
            _land_squash_mod, "_tick005_land_regressions", lambda *a, **k: ("T-9999",)
        )

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.TerminalStateRegression

        # root must be unwound back to exactly its pre-land tip -- nothing
        # from the refused land's squash-apply may remain staged/committed.
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == pre_sha
        assert _status_ignoring_frob(repo) == ""
