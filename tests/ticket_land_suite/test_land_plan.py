from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from typani.result import Err, Ok, Result

import frob.tickets._land_squash as _land_squash_mod
from frob.gitio import GitError, ProcResult
from frob.tickets import (
    Origin,
    TicketState,
    new_ticket,
)
from frob.tickets._models import (
    LandError,
    Ticket,
)
from frob.tickets._new_renumber import _ticket_from_spec
from frob.tickets._store import (
    load_all,
    write_ticket,
)
from tests.ticket_land_suite.conftest import (
    _commit_all,
    _git_init,
    _make_design_worktree,
    _run,
    _spec,
    _status_ignoring_frob,
)

pytestmark = pytest.mark.heavy_subprocess



# frob:ticket T-1269
# frob:ticket T-2198
class TestLandPlan:
    """T-1269: `frob ticket land --plan` -- atomic design-phase land with
    automatic draft finalization. Real git subprocesses/worktrees,
    matching this whole file's established style."""

    # frob:ticket T-1269
    # frob:tests tests/ticket_land_suite/test_land_plan.py::TestLandPlan.test_merges_and_finalizes_every_draft_atomically  # noqa: E501
    def test_merges_and_finalizes_every_draft_atomically(
        self, repo: Path, tmp_path: Path
    ) -> None:
        from frob.tickets._land import land_plan

        worktree = _make_design_worktree(repo, tmp_path)
        (worktree / "docs").mkdir()
        (worktree / "docs" / "new.md").write_text("# New doc\n")
        draft = new_ticket(
            worktree,
            _spec("A design-phase draft ticket"),
        ).danger_ok
        assert draft.id.startswith("T-draft-")
        _commit_all(worktree, "docs: add new.md + file draft")

        result = land_plan(repo, worktree)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert not report.dry_run
        assert report.merge_commit is not None
        assert report.commit_sha is not None
        assert len(report.finalized) == 1
        old_id, new_id = report.finalized[0]
        assert old_id == draft.id
        assert new_id.startswith("T-") and not new_id.startswith("T-draft-")

        # The finalized id (never the draft id) is what actually landed.
        loaded = load_all(repo).danger_ok
        assert new_id in loaded
        assert draft.id not in loaded
        assert (repo / "docs" / "new.md").exists()
        # Landing left root clean -- no half-merged state, no stray lock.
        assert _status_ignoring_frob(repo) == ""

    # frob:ticket T-1269
    # frob:tests \
    # tests/ticket_land_suite/test_land_plan.py::TestLandPlan.test_dry_run_unwinds_the_\
    # merge
    def test_dry_run_unwinds_the_merge(self, repo: Path, tmp_path: Path) -> None:
        from frob.tickets._land import land_plan

        worktree = _make_design_worktree(repo, tmp_path)
        (worktree / "docs").mkdir()
        (worktree / "docs" / "new.md").write_text("# New doc\n")
        _commit_all(worktree, "docs: add new.md")

        pre_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        result = land_plan(repo, worktree, dry_run=True)
        assert result.is_ok, result.err
        assert result.danger_ok.dry_run
        # root is back at its pre-merge tip -- nothing landed for real.
        post_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert post_sha == pre_sha
        assert not (repo / "docs" / "new.md").exists()

    # frob:ticket T-1269
    # frob:tests \
    # tests/ticket_land_suite/test_land_plan.py::TestLandPlan.test_merge_conflict_abort\
    # s_and_refuses
    def test_merge_conflict_aborts_and_refuses(
        self, repo: Path, tmp_path: Path
    ) -> None:
        from frob.tickets._land import land_plan

        worktree = _make_design_worktree(repo, tmp_path)
        (worktree / "src" / "feature.py").write_text("# worktree edit\n")
        _commit_all(worktree, "conflicting edit")

        # A genuine, real textual conflict on the SAME line in root.
        (repo / "src" / "feature.py").write_text("# root edit\n")
        _commit_all(repo, "root edit")

        pre_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        result = land_plan(repo, worktree)
        assert result.is_err
        assert result.danger_err is LandError.MergeConflict
        # The conflicted merge was aborted -- root is clean and unmoved.
        assert _status_ignoring_frob(repo) == ""
        post_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert post_sha == pre_sha

    # frob:ticket T-1269
    # frob:ticket T-1522
    # frob:tests tests/ticket_land_suite/test_land_plan.py::TestLandPlan.test_tick_gate_dirty_unwinds_finalize_but_keeps_the_durable_merge  # noqa: E501
    def test_tick_gate_dirty_unwinds_finalize_but_keeps_the_durable_merge(
        self, repo: Path, tmp_path: Path
    ) -> None:
        """T-1522: pre-T-1522 this fully unwound back to the pre-merge tip
        on a dirty TICK-gate re-check, discarding the merge commit itself
        -- the exact shape that ate the T-1199/T-1200 queue-drain commits
        in the 2026-08-04 incident when a LATER, unrelated step failed in
        the same invocation. The merge commit is now a durable checkpoint:
        only the finalize-renumbering commit on top of it is undone."""
        from frob.tickets._land import land_plan

        worktree = _make_design_worktree(repo, tmp_path)
        (worktree / "docs").mkdir()
        (worktree / "docs" / "new.md").write_text("# New doc\n")
        draft = new_ticket(worktree, _spec("Another draft")).danger_ok
        _commit_all(worktree, "docs: add new.md + file draft")

        pre_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        result = land_plan(repo, worktree, check_ticks=lambda: False)
        assert result.is_err
        assert result.danger_err is LandError.PlanTickGateDirty
        # The merge commit persists (T-1522): the doc file it carried
        # survives, and root's tip moved past the pre-merge sha even
        # though this call reported an error.
        post_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert post_sha != pre_sha
        assert (repo / "docs" / "new.md").exists()
        # Only the finalize step (draft -> real id renumbering) is
        # undone: the draft's id is back as a draft, not finalized to a
        # real id anywhere on root.
        loaded = load_all(repo).danger_ok
        assert draft.id in loaded
        assert loaded[draft.id].id.startswith("T-draft-")

    # frob:ticket T-2189
    # frob:tests tests/ticket_land_suite/test_land_plan.py::TestLandPlan.test_dry_run_tick_gate_dirty_still_fully_unwinds  # noqa: E501
    def test_dry_run_tick_gate_dirty_still_fully_unwinds(
        self, repo: Path, tmp_path: Path
    ) -> None:
        """T-2189: DESIGNATED REPRO. Pre-fix, `_land_plan_locked`'s
        `PlanTickGateDirty` branch called `_land_plan_unwind_after_merge`
        with no knowledge of `dry_run` at all -- it always ran T-1522's
        stop-at-the-merge-commit policy, correct for a REAL land but not
        for a `--dry-run` one. A real incident: `frob ticket land --plan
        --dry-run` against a worktree whose merge succeeds but whose
        `check_ticks()` reports dirty reported `PlanTickGateDirty` and
        claimed a full unwind, while root's tip had actually moved to a
        real merge commit -- a mutation from a call that promised none,
        with the draft-finalize step never reached because the dirty
        check fired first. This must leave root's tip fully unmoved,
        exactly like the non-dirty dry-run path
        (`test_dry_run_unwinds_the_merge` above) and the durable-merge
        REAL-land path (`test_tick_gate_dirty_unwinds_finalize_but_keeps_
        the_durable_merge` above) must stay unchanged by this fix."""
        from frob.tickets._land import land_plan

        worktree = _make_design_worktree(repo, tmp_path)
        (worktree / "docs").mkdir()
        (worktree / "docs" / "new.md").write_text("# New doc\n")
        draft = new_ticket(worktree, _spec("A dry-run-dirty draft")).danger_ok
        _commit_all(worktree, "docs: add new.md + file draft")

        pre_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        result = land_plan(repo, worktree, dry_run=True, check_ticks=lambda: False)
        assert result.is_err
        assert result.danger_err is LandError.PlanTickGateDirty
        # root's tip is COMPLETELY unmoved -- no merge commit, no
        # finalize commit, nothing reachable from root's HEAD that this
        # dry run produced.
        post_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert post_sha == pre_sha
        assert not (repo / "docs" / "new.md").exists()
        # No draft was finalized -- it is still a draft, and it is not
        # present on root at all (the merge itself was fully reverted).
        loaded = load_all(repo).danger_ok
        assert draft.id not in loaded

    # frob:ticket T-1269
    # frob:tests tests/ticket_land_suite/test_land_plan.py::TestLandPlan.test_cli_dispatches_to_land_plan_and_reports  # noqa: E501
    def test_cli_dispatches_to_land_plan_and_reports(
        self, repo: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        from frob.app.config import AppConfig
        from frob.app.ticket_runner._land_cmd import _land

        worktree = _make_design_worktree(repo, tmp_path)
        (worktree / "docs").mkdir()
        (worktree / "docs" / "new.md").write_text("# New doc\n")
        _commit_all(worktree, "docs: add new.md")

        cfg = AppConfig(
            ticket_command="land",
            ticket_land_plan=True,
            ticket_worktree=worktree,
            ticket_path=repo,
        )
        with caplog.at_level("INFO"):
            _land(repo, cfg)
        assert any("landed onto" in rec.message for rec in caplog.records)
        assert (repo / "docs" / "new.md").exists()

    # frob:ticket T-2198
    # frob:tests \
    # tests/ticket_land_suite/test_land_plan.py::TestLandPlan.test_pre_existing_tick004_does_not_block_ledger_only_plan_land  # noqa: E501
    def test_pre_existing_tick004_does_not_block_ledger_only_plan_land(
        self, repo: Path, tmp_path: Path
    ) -> None:
        """T-2198: DESIGNATED REPRO. Pre-fix, `_land_plan_check_ticks_fn`
        gated `--plan` on `frob check --only tickets`'s GLOBAL error count
        being zero -- so an unrelated, pre-existing rotting-epic TICK004
        alarm (measured in this repo's own history: 9 of them, all
        `tier=epic`, 15-20 days old) refused a purely ledger-only land
        (128 insertions, one new ticket file, zero source files) with
        `PlanTickGateDirty`, even though decomposing that rotting epic
        into leaves is itself ledger-only work `--plan` exists to carry.
        This test seeds exactly that shape -- one already-rotten CRITICAL
        ticket on `main`, unrelated to the landing worktree's own
        ledger-only draft -- and MUST FAIL against pre-fix `main`."""
        from datetime import timedelta

        from frob.tickets._models import Priority, TicketKind

        # `repo` has no `pyproject.toml`/root-level `.py` sentinel, so a
        # real `frob check` spawn against it reports `unknown-project-
        # type` (CHECK001) before the `tickets` gate family ever runs --
        # this designated repro needs a REAL `gate:TICK` evaluation, so
        # give it one.
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.0.0"\n'
        )
        _commit_all(repo, "chore: add pyproject.toml so frob check can dispatch")

        # A pre-existing, already-rotten ticket on `root` -- CRITICAL
        # priority rots at 3 days (escalates to ERROR severity past 2x =
        # 6 days); 10 days old guarantees a TICK004 ERROR finding, wholly
        # unrelated to anything the landing worktree touches.
        rotten = Ticket(
            id="T-9001",
            title="A pre-existing rotting epic, unrelated to this land",
            state=TicketState.QUEUED,
            kind=TicketKind.FEATURE,
            origin=Origin.HUMAN,
            created=date.today() - timedelta(days=10),
            priority=Priority.CRITICAL,
        )
        assert write_ticket(repo, rotten).is_ok
        _commit_all(repo, "chore(tickets): seed a pre-existing rotting epic")

        # A purely ledger-only worktree: one new draft ticket, zero
        # source files -- the T-2197 shape the ticket's Description
        # measured being refused.
        worktree = _make_design_worktree(repo, tmp_path)
        draft = new_ticket(
            worktree,
            _spec("A ledger-only draft, unrelated to the rotten ticket"),
        ).danger_ok
        # `new_ticket` already auto-commits the ledger write -- no
        # separate commit needed (unlike the docs-file fixtures elsewhere
        # in this class).

        from frob.app.config import AppConfig
        from frob.app.ticket_runner._land_cmd import _land

        cfg = AppConfig(
            ticket_command="land",
            ticket_land_plan=True,
            ticket_worktree=worktree,
            ticket_path=repo,
        )
        # T-2198: this MUST succeed -- the landing worktree's own diff
        # (one new draft ticket, zero source files) did not cause the
        # pre-existing TICK004 finding, so --plan must not refuse on its
        # account. Pre-fix, `_land_plan_check_ticks_fn` gated on the
        # GLOBAL TICK-gate count and `_land_plan_cmd` called `sys.exit(1)`
        # here -- this assertion is the designated repro.
        try:
            _land(repo, cfg)
        except SystemExit as exc:
            pytest.fail(
                "T-2198: --plan refused a ledger-only land (sys.exit"
                f"({exc.code})) solely because of an UNRELATED "
                "pre-existing TICK004 rotting-epic alarm on main -- "
                "attribution, not a global count, is the fix"
            )
        loaded = load_all(repo).danger_ok
        assert draft.id not in loaded
        assert any(
            t.title == "A ledger-only draft, unrelated to the rotten ticket"
            for t in loaded.values()
        )


# frob:ticket T-1495
class TestLandPlanUnwindNeverDiscardsForeignCommits:
    """T-1495 (the 2026-08-04 incident): `land_plan`'s own unwind path
    (`_land_plan_reset_hard`) used to `reset --hard` unconditionally --
    if ANOTHER process committed to `root` after this run's own last
    commit but before the reset ran (a concurrent queue-drain land, a
    manual `frob ticket drop`), that foreign commit was silently
    destroyed along with this run's own half-finished work. The fix
    (`_assert_reset_only_discards_own_commits`) refuses instead."""

    # frob:ticket T-1495
    # frob:tests tests/ticket_land_suite/test_land_plan.py::TestLandPlanUnwindNeverDiscardsForeignCommits.test_foreign_commit_after_own_last_commit_refuses_instead_of_discarding  # noqa: E501
    def test_foreign_commit_after_own_last_commit_refuses_instead_of_discarding(
        self, repo: Path, tmp_path: Path
    ) -> None:
        from frob.tickets._land import land_plan

        worktree = _make_design_worktree(repo, tmp_path)
        (worktree / "docs").mkdir()
        (worktree / "docs" / "new.md").write_text("# New doc\n")
        _commit_all(worktree, "docs: add new.md")

        # check_ticks() simulates a FOREIGN process committing to root
        # (another land's queue-drain, a manual `frob ticket drop`)
        # DURING this invocation's own window, then reports dirty --
        # exactly the interleaving shape the 2026-08-04 incident hit.
        def foreign_commit_then_dirty() -> bool:
            (repo / "foreign.txt").write_text("someone else's work\n")
            _commit_all(repo, "chore: an unrelated interleaved commit")
            return False

        pre_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        result = land_plan(repo, worktree, check_ticks=foreign_commit_then_dirty)
        assert result.is_err
        assert result.danger_err is LandError.GitFailed
        # The foreign commit MUST survive -- root's tip must NOT have been
        # reset back past it, unlike the pre-T-1495 behavior.
        post_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert post_sha != pre_sha
        assert (repo / "foreign.txt").exists()
        log = _run(["git", "log", "--oneline"], repo).stdout
        assert "an unrelated interleaved commit" in log

    # frob:ticket T-1740
    def test_foreign_commit_refusal_still_unstages_own_leftover_content(
        self, repo: Path, tmp_path: Path
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_land_plan.py::TestLandPlanUnwindNeverDiscardsForeignCommits.test_foreign_commit_refusal_still_unstages_own_leftover_content  # noqa: E501
        """T-1740's second instance of the same defect class: `land
        --plan` runs its OWN unwind primitive (T-1495), separate from
        `_verified_reset_root`, with the identical gap -- refusing on
        foreign-commit detection used to leave whatever this run itself
        had staged sitting in root's index. Never allowed to reach the
        `_land_plan_reset_hard` unwind itself (the tip mismatch refuses
        first), so THIS staged content is whatever `check_ticks()`
        itself leaves in the index while faking the foreign interleave."""
        from frob.tickets._land import land_plan

        worktree = _make_design_worktree(repo, tmp_path)
        (worktree / "docs").mkdir()
        (worktree / "docs" / "new.md").write_text("# New doc\n")
        _commit_all(worktree, "docs: add new.md")

        def foreign_commit_and_leave_staged() -> bool:
            (repo / "foreign.txt").write_text("someone else's work\n")
            _commit_all(repo, "chore: an unrelated interleaved commit")
            (repo / "leftover_staged.txt").write_text("left behind by this run\n")
            _run(["git", "add", "leftover_staged.txt"], repo)
            return False

        result = land_plan(repo, worktree, check_ticks=foreign_commit_and_leave_staged)
        assert result.is_err
        assert result.danger_err is LandError.GitFailed
        staged = _run(["git", "diff", "--cached", "--name-only"], repo).stdout.strip()
        assert staged == "", (
            "land --plan's own T-1495 unwind path left staged content "
            "behind -- the T-1740 incident, reproduced in the --plan path"
        )

    # frob:ticket T-1495
    # frob:ticket T-1522
    # frob:tests tests/ticket_land_suite/test_land_plan.py::TestLandPlanUnwindNeverDiscardsForeignCommits.test_no_foreign_commit_unwinds_to_the_merge_commit_not_pre_merge  # noqa: E501
    def test_no_foreign_commit_unwinds_to_the_merge_commit_not_pre_merge(
        self, repo: Path, tmp_path: Path
    ) -> None:
        """The ordinary, non-interleaved case: no foreign commit landed,
        so the unwind still runs -- but (T-1522) it now stops at the
        merge commit rather than the pre-merge tip, since the merge
        commit is a durable checkpoint, not something a later, unrelated
        failure in the same invocation should discard."""
        from frob.tickets._land import land_plan

        worktree = _make_design_worktree(repo, tmp_path)
        (worktree / "docs").mkdir()
        (worktree / "docs" / "new.md").write_text("# New doc\n")
        _commit_all(worktree, "docs: add new.md")

        pre_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        result = land_plan(repo, worktree, check_ticks=lambda: False)
        assert result.is_err
        assert result.danger_err is LandError.PlanTickGateDirty
        post_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert post_sha != pre_sha
        assert (repo / "docs" / "new.md").exists()



# frob:ticket T-1522
# frob:ticket T-2220
class TestLandPlanQueueDrainCommitsDurable:
    """T-1522: the exact 2026-08-04 T-1199/T-1200 incident shape --
    `land_plan`'s merge step already durably carries a shared worktree
    branch's OTHER, queue-drained content onto `root` (a doc file, other
    already-merged tickets) before the finalize step runs at all. A
    finalize failure AFTER that merge succeeded must not discard it."""

    # frob:ticket T-1522
    # frob:ticket T-2220
    # frob:tests tests/ticket_land_suite/test_land_plan.py::TestLandPlanQueueDrainCommitsDurable.test_finalize_failure_after_merge_keeps_the_merge_commit  # noqa: E501
    def test_finalize_failure_after_merge_keeps_the_merge_commit(
        self, repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.tickets import _land as land_module
        from frob.tickets._land import land_plan
        from frob.tickets._models import LandError as _LandError

        worktree = _make_design_worktree(repo, tmp_path)
        (worktree / "docs").mkdir()
        (worktree / "docs" / "new.md").write_text("# New doc\n")
        _commit_all(worktree, "docs: add new.md -- the 'queue-drained' content")

        # Simulate a finalize failure (a `NotFound` from `finalize_draft`,
        # or any other post-merge finalize error) AFTER the merge commit
        # already exists on root -- exactly the 2026-08-04 shape where
        # something unrelated to the already-merged content fails.
        def _always_fails(_root: Path, _merge_commit: str) -> Result[tuple, _LandError]:
            return Err(_LandError.NotFound)

        monkeypatch.setattr(land_module, "_land_plan_finalize_drafts", _always_fails)

        pre_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        result = land_plan(repo, worktree)
        assert result.is_err
        assert result.danger_err is LandError.NotFound

        # T-1522: the merge commit persists -- root's tip moved past the
        # pre-merge sha (it now IS the merge commit) and the doc file it
        # carried is on disk, even though this invocation reported an
        # error for the (unrelated) finalize failure.
        post_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert post_sha != pre_sha
        assert (repo / "docs" / "new.md").exists()

        # A retry of land_plan against the now-advanced root is a clean
        # no-op merge (nothing new to bring in) -- proving the content is
        # genuinely durable, not merely "not yet reset" mid-call.
        monkeypatch.undo()
        retry = land_plan(repo, worktree)
        assert retry.is_ok, retry.err




# frob:ticket T-1349
class TestLandSquashHelpersMutationCoverage:
    """T-1349: same rationale as `TestLandReleaseMonotonicityHelpers` above,
    for the squash-apply/close family T-1334 moved into `_land_squash.py`.
    Each test targets one specific surviving mutant the T-1349 mutation
    run found, not a re-assertion of "the tests cover it structurally"."""

    def test_worktree_full_changeset_diff_ok_but_nonzero_returncode_is_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_land_plan.py::TestLandSquashHelpersMutationCoverage.test_worktree_full_changeset_diff_ok_but_nonzero_returncode_is_failed  # noqa: E501
        """Kills the `or` -> `and` mutant on `_worktree_full_changeset`'s
        diff guard: `git diff` succeeding at the process level (is_err=
        False) with a nonzero returncode must still refuse as
        `GitFailed`, not fall through to parsing `stdout`."""
        root = tmp_path / "repo"
        _git_init(root)
        (root / "f.txt").write_text("x")
        _commit_all(root, "init")
        wt = tmp_path / "wt"
        _run(["git", "worktree", "add", "-b", "feat-changeset", str(wt)], root)
        (wt / "g.txt").write_text("y")
        _commit_all(wt, "add g")

        real_run_argv = _land_squash_mod.run_argv

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            if "diff" in argv and "--name-only" in argv:
                return Ok(
                    ProcResult(
                        argv=tuple(argv),
                        returncode=129,
                        stdout="",
                        stderr="fatal: ambiguous argument",
                    )
                )
            return real_run_argv(argv, **kwargs)

        monkeypatch.setattr(_land_squash_mod, "run_argv", _fake_run_argv)
        result = _land_squash_mod._worktree_full_changeset(wt, "main")
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_land_commit_details_diff_tree_fails_returns_empty_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_land_plan.py::TestLandSquashHelpersMutationCoverage.test_land_commit_details_diff_tree_fails_returns_empty_files  # noqa: E501
        """Kills the `and` -> `or` mutant on `_land_commit_details`'s
        `files` derivation: when `diff-tree` itself fails (`Err`), the
        `and` guard must short-circuit to `()` without ever touching
        `stat.danger_ok` -- an `or` mutant instead evaluates
        `stat.danger_ok.returncode` unconditionally on the `Err` branch
        and crashes."""

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            if "rev-parse" in argv:
                return Ok(
                    ProcResult(
                        argv=tuple(argv), returncode=0, stdout="deadbeef\n", stderr=""
                    )
                )
            return Err(GitError.GitFailed)

        monkeypatch.setattr(_land_squash_mod, "run_argv", _fake_run_argv)
        sha_str, files = _land_squash_mod._land_commit_details(tmp_path)
        assert sha_str == "deadbeef"
        assert files == ()

    def test_absorption_scoped_content_matches_worktree_head_err_is_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_land_plan.py::TestLandSquashHelpersMutationCoverage.test_absorption_scoped_content_matches_worktree_head_err_is_false  # noqa: E501
        """Kills the `False` -> `True` negation mutant guarding
        `_absorption_scoped_content_matches`'s `worktree_head` error path:
        an unresolvable worktree HEAD must read as "not verified", never
        a confirmed match."""
        ticket = _ticket_from_spec("T-0001", _spec("t", scope=("x",)), ())
        monkeypatch.setattr(
            _land_squash_mod, "_rev_parse", lambda root, ref: Err(GitError.GitFailed)
        )
        result = _land_squash_mod._absorption_scoped_content_matches(
            tmp_path, tmp_path, ticket
        )
        assert result is False

    def test_absorption_scoped_content_matches_diff_ok_but_nonzero_is_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_land_plan.py::TestLandSquashHelpersMutationCoverage.test_absorption_scoped_content_matches_diff_ok_but_nonzero_is_false  # noqa: E501
        """Kills both the `or` -> `and` mutant on the diff guard AND the
        `False` -> `True` negation on its return: `git diff` succeeding at
        the process level with a nonzero returncode must still read as
        unverified (`False`)."""
        ticket = _ticket_from_spec("T-0001", _spec("t", scope=("x",)), ())
        monkeypatch.setattr(
            _land_squash_mod, "_rev_parse", lambda root, ref: Ok("deadbeef")
        )
        monkeypatch.setattr(
            _land_squash_mod,
            "run_argv",
            lambda argv, **kwargs: Ok(
                ProcResult(
                    argv=tuple(argv), returncode=1, stdout="", stderr="diff failed"
                )
            ),
        )
        result = _land_squash_mod._absorption_scoped_content_matches(
            tmp_path, tmp_path, ticket
        )
        assert result is False

    def test_absorption_verified_false_when_ticket_not_done(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_land_plan.py::TestLandSquashHelpersMutationCoverage.test_absorption_verified_false_when_ticket_not_done  # noqa: E501
        """Kills the `and` -> `or` mutant on `_absorption_verified`'s
        guard: a ticket loaded successfully but NOT yet `done` must
        short-circuit to `False` WITHOUT ever consulting
        `_absorption_scoped_content_matches` -- an `or` mutant instead
        treats `is_err=False` alone as sufficient to skip the early
        return, letting a not-done ticket fall through to whatever
        `_absorption_scoped_content_matches` says."""
        ticket = _ticket_from_spec("T-0001", _spec("t", scope=("x",)), ())
        not_done = ticket.model_copy(update={"state": TicketState.QUEUED})
        monkeypatch.setattr("frob.tickets._load_one", lambda root, tid: Ok(not_done))
        # If the early-return guard is mutated away, this stub's `True`
        # would leak through as the final result -- the real code must
        # never reach it.
        monkeypatch.setattr(
            _land_squash_mod, "_absorption_scoped_content_matches", lambda *a: True
        )
        result = _land_squash_mod._absorption_verified(
            tmp_path, tmp_path, ticket, "T-0001"
        )
        assert result is False

    def test_absorption_verified_false_when_load_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_land_plan.py::TestLandSquashHelpersMutationCoverage.test_absorption_verified_false_when_load_fails  # noqa: E501
        """Complement of the above: a failed ledger load also returns
        `False`, killing the `False` -> `True` negation mutant on the
        shared early-return statement."""
        ticket = _ticket_from_spec("T-0001", _spec("t", scope=("x",)), ())
        monkeypatch.setattr("frob.tickets._load_one", lambda root, tid: Err("boom"))
        result = _land_squash_mod._absorption_verified(
            tmp_path, tmp_path, ticket, "T-0001"
        )
        assert result is False

    def test_report_stacked_sibling_absorption_reports_real_land_not_dry_run(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_land_plan.py::TestLandSquashHelpersMutationCoverage.test_report_stacked_sibling_absorption_reports_real_land_not_dry_run  # noqa: E501
        """Kills the literal `False` -> `True` negation mutants on
        `_report_stacked_sibling_absorption`'s `dry_run=False` and
        `natives_rebuilt=False` fields: an absorbed-land report always
        describes a REAL (non-dry-run) land that rebuilt nothing new,
        regardless of the caller's own dry-run status."""
        monkeypatch.setattr(
            _land_squash_mod, "_rev_parse", lambda root, ref: Ok("cafef00d")
        )
        report = _land_squash_mod._report_stacked_sibling_absorption(
            tmp_path, "T-0001", "T-0001", True, True
        )
        assert report.dry_run is False
        assert report.natives_rebuilt is False
        assert report.ledger_spliced is False
        assert report.commit_sha == "cafef00d"

    def test_absorbed_land_report_none_when_staged_files_nonempty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_land_plan.py::TestLandSquashHelpersMutationCoverage.test_absorbed_land_report_none_when_staged_files_nonempty  # noqa: E501
        """Kills the `or` -> `and` mutant on `_absorbed_land_report`'s
        first guard: a NON-EMPTY staged set (a genuine partial squash,
        not an absorbed no-op) must short-circuit to `None` even though
        `_staged_files` itself succeeded (`is_err=False`) -- an `and`
        mutant instead requires BOTH `is_err` and a truthy staged set,
        so a successful-but-nonempty read wrongly falls through toward
        `_absorption_verified`."""
        ticket = _ticket_from_spec("T-0001", _spec("t", scope=("x",)), ())
        monkeypatch.setattr(
            _land_squash_mod,
            "_staged_files",
            lambda root: Ok(frozenset({"some/file.py"})),
        )
        # If the guard is mutated away, this stub's `True` would let
        # execution reach `_report_stacked_sibling_absorption` instead of
        # returning `None` -- assert it never does.
        monkeypatch.setattr(_land_squash_mod, "_absorption_verified", lambda *a: True)
        result = _land_squash_mod._absorbed_land_report(
            tmp_path, tmp_path, tmp_path, ticket, "T-0001", "T-0001", True, True
        )
        assert result is None

    def test_staged_files_diff_ok_but_nonzero_returncode_is_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_land_plan.py::TestLandSquashHelpersMutationCoverage.test_staged_files_diff_ok_but_nonzero_returncode_is_failed  # noqa: E501
        """Kills the `or` -> `and` mutant on `_staged_files`'s diff guard:
        `git diff --cached` succeeding at the process level with a
        nonzero returncode must still refuse as `GitFailed`."""
        monkeypatch.setattr(
            _land_squash_mod,
            "run_argv",
            lambda argv, **kwargs: Ok(
                ProcResult(
                    argv=tuple(argv), returncode=1, stdout="", stderr="diff failed"
                )
            ),
        )
        result = _land_squash_mod._staged_files(tmp_path)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_land_commit_details_rev_parse_ok_but_nonzero_returncode_is_no_sha(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_land_plan.py::TestLandSquashHelpersMutationCoverage.test_land_commit_details_rev_parse_ok_but_nonzero_returncode_is_no_sha  # noqa: E501
        """Kills the `and` -> `or` mutant on `_land_commit_details`'s `sha`
        derivation: `rev-parse` succeeding at the process level with a
        nonzero returncode must still report `sha_str=None`, not the
        (meaningless in this case) stdout an `or` mutant would accept."""

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            if "rev-parse" in argv:
                return Ok(
                    ProcResult(
                        argv=tuple(argv),
                        returncode=128,
                        stdout="stale-sha\n",
                        stderr="fatal",
                    )
                )
            return Ok(ProcResult(argv=tuple(argv), returncode=0, stdout="", stderr=""))

        monkeypatch.setattr(_land_squash_mod, "run_argv", _fake_run_argv)
        sha_str, files = _land_squash_mod._land_commit_details(tmp_path)
        assert sha_str is None
